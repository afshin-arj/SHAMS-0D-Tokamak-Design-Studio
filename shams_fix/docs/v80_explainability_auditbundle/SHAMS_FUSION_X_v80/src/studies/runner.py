from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from solvers.constraint_solver import solve_for_targets
from constraints.constraints import evaluate_constraints
from shams_io.run_artifact import build_run_artifact, write_run_artifact, read_run_artifact
from decision.reference_design import synthesize_reference_design
from .spec import StudySpec
from .uq import run_uq
from .index_db import SQLiteIndex
from shams_io.provenance import collect_provenance


def _build_study_summary(index: Dict[str, Any]) -> Dict[str, Any]:
    cases = index.get("cases", []) or []
    n = int(index.get("n_cases", len(cases)) or len(cases))
    n_ok = sum(1 for c in cases if bool(c.get("ok", False)))
    # Dominant blockers distribution if available in per-case artifacts
    blockers: Dict[str, int] = {}
    for c in cases:
        msg = str(c.get("message", ""))
        if not msg:
            continue
        key = msg.split(";")[0].strip()
        if key:
            blockers[key] = int(blockers.get(key, 0) + 1)
    top_blockers = sorted(blockers.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "schema_version": "study_summary.v1",
        "created_unix": index.get("created_unix"),
        "n_cases": n,
        "n_ok": n_ok,
        "ok_fraction": (float(n_ok) / float(max(n, 1))),
        "top_solver_messages": [{"message": k, "count": v} for k, v in top_blockers],
        "reference_design": index.get("reference_design"),
        "nonfeasibility_certificate": index.get("nonfeasibility_certificate"),
    }


def _run_case_worker(args: Dict[str, Any]) -> Dict[str, Any]:
    """Worker to run one case (pickle-safe)."""
    idx = int(args["idx"])
    base_dict = args["base_dict"]
    upd = args["upd"]
    targets = args["targets"]
    out_dir = Path(args["out_dir"])
    subsystems = args.get("subsystems")
    baseline_inputs = args.get("baseline_inputs")

    base = PointInputs.from_dict(base_dict)
    d = dict(base.to_dict())
    d.update(upd)
    inp = PointInputs.from_dict(d)

    res = solve_for_targets(inp, targets=targets, variables=args["variables"], max_iter=int(args["max_iter"]), tol=float(args["tol"]), damping=float(args["damping"]))
    out = res.out or {}
    cons = evaluate_constraints(out)
    art = build_run_artifact(inputs=dict(inp.__dict__), outputs=dict(out), constraints=cons,
                             meta={"mode":"study"}, solver={"message": res.message, "trace": res.trace or []},
                             subsystems=subsystems, baseline_inputs=baseline_inputs)
    fname = out_dir / f"case_{idx:04d}.json"
    write_run_artifact(fname, art)

    row = {"case": idx, "ok": bool(res.ok), "iters": int(res.iters), "message": res.message, "path": str(fname)}
    for k,v in upd.items():
        try: row[f"in_{k}"] = float(v)
        except Exception: row[f"in_{k}"] = v
    for k,v in targets.items():
        try: row[f"t_{k}"] = float(v)
        except Exception: row[f"t_{k}"] = v
    for k in targets.keys():
        try: row[f"ach_{k}"] = float(out.get(k, float("nan")))
        except Exception: row[f"ach_{k}"] = out.get(k)
    return row
def _apply_updates(base: PointInputs, upd: Dict[str, Any]) -> PointInputs:
    d = base.to_dict()
    for k,v in (upd or {}).items():
        d[str(k)] = v
    return PointInputs.from_dict(d)

def run_study(spec: StudySpec, out_dir: str | Path, *, label_prefix: str = "") -> Dict[str, Any]:
    """Run a sweep study headlessly and write per-case artifacts + an index."""
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)

    # Base inputs: start from preset if provided, else from defaults.
    # We keep this dependency-light by importing presets lazily.
    base = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    if spec.base_preset:
        try:
            if spec.base_preset in REFERENCE_MACHINES:
                base = _apply_updates(base, REFERENCE_MACHINES[spec.base_preset])
        except Exception:
            pass
    if spec.base_inputs:
        base = _apply_updates(base, spec.base_inputs)

    cases: List[Dict[str, Any]] = []
    t0 = time.time()

    # Cartesian sweep
    sweep_vars = spec.sweeps or []
    grids: List[Tuple[str, List[float]]] = [(sv.name, sv.values) for sv in sweep_vars if sv.values]
    def rec(i: int, cur: Dict[str, float]):
        if i >= len(grids):
            cases.append(dict(cur))
            return
        name, vals = grids[i]
        for v in vals:
            cur[name] = float(v)
            rec(i+1, cur)
    rec(0, {})

    if not cases:
        cases = [{}]

    # Variables for solve_for_targets: (x0, lo, hi)
    variables: Dict[str, Tuple[float, float, float]] = {}
    for k, v in (spec.variables or {}).items():
        try:
            x0, lo, hi = v
            variables[str(k)] = (float(x0), float(lo), float(hi))
        except Exception:
            continue

    index_rows: List[Dict[str, Any]] = []
    # Execute cases (optionally parallel)
    n_workers = max(1, int(getattr(spec, "n_workers", 1) or 1))
    subsystems = {"fidelity": spec.fidelity or {}, "calibration": spec.calibration or {}}
    baseline_inputs = dict(base.__dict__)
    if bool(getattr(spec, "use_sqlite_index", False)):
        db = SQLiteIndex(outp/"index.sqlite")
    else:
        db = None

    if n_workers == 1:
        for idx, upd in enumerate(cases):
            row = _run_case_worker({
                "idx": idx,
                "base_dict": dict(base.__dict__),
                "upd": upd,
                "targets": dict(spec.targets),
                "variables": variables,
                "max_iter": spec.max_iter,
                "tol": spec.tol,
                "damping": spec.damping,
                "out_dir": str(outp),
                "subsystems": subsystems,
                "baseline_inputs": baseline_inputs,
            })
            index_rows.append(row)
            if db is not None:
                db.add_case(row["case"], row["ok"], row["iters"], str(row.get("message","")), str(row.get("path","")))
    else:
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as ex:
            futs = []
            for idx, upd in enumerate(cases):
                futs.append(ex.submit(_run_case_worker, {
                    "idx": idx,
                    "base_dict": dict(base.__dict__),
                    "upd": upd,
                    "targets": dict(spec.targets),
                    "variables": variables,
                    "max_iter": spec.max_iter,
                    "tol": spec.tol,
                    "damping": spec.damping,
                    "out_dir": str(outp),
                    "subsystems": subsystems,
                    "baseline_inputs": baseline_inputs,
                }))
            for f in as_completed(futs):
                row = f.result()
                index_rows.append(row)
                if db is not None:
                    db.add_case(row["case"], row["ok"], row["iters"], str(row.get("message","")), str(row.get("path","")))
        # keep stable order
        index_rows.sort(key=lambda r: int(r.get("case",0)))

    if db is not None:
        db.close()

    # Reference design synthesis (decision-grade): choose one representative design from feasible cases.
    artifacts=[]
    for row in index_rows:
        p=row.get("path")
        if not p:
            continue
        try:
            a=read_run_artifact(Path(p))
            if isinstance(a, dict):
                a["_path"]=p
                artifacts.append(a)
        except Exception:
            pass
    ref = synthesize_reference_design(artifacts)
    nonfeas = None
    if ref is None:
        # Use the first available non-feasibility certificate, if present.
        for a in artifacts:
            n = a.get('nonfeasibility_certificate')
            if isinstance(n, dict) and n:
                nonfeas = n
                break

    index = {
        "schema_version": "study_index.v1",
        "study": asdict(spec),
        "created_unix": time.time(),
        "elapsed_s": time.time()-t0,
        "n_cases": len(index_rows),
        "cases": index_rows,
        "reference_design": ref,
        "nonfeasibility_certificate": nonfeas,
        "provenance": collect_provenance(Path(__file__).resolve()),
    }
    (outp/"index.json").write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

    # Study summary (stable, schema-versioned)
    try:
        summary = _build_study_summary(index)
        (outp/"study_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass

    return index
