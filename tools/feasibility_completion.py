from __future__ import annotations
"""Feasibility Completion Engine (v133)

Given partial inputs (fixed) and a set of free/uncertain parameters with bounds,
search for feasible completions using sampling (deterministic by default).

Safety:
- Calls existing evaluator only (no physics/solver changes)
- Produces audit-ready report + bundle zip
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO, StringIO
import json, time, hashlib, zipfile, csv, random, math

from tools.study_matrix import evaluate_point_inputs

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def linspace(a: float, b: float, n: int) -> List[float]:
    if n <= 1:
        return [float(a)]
    return [float(a) + (float(b)-float(a))*i/(n-1) for i in range(n)]

def _safe_float(x):
    try:
        if x is None: return None
        if isinstance(x, bool): return None
        return float(x)
    except Exception:
        return None

def _product(grids: List[List[float]]):
    if not grids:
        yield tuple()
        return
    import itertools
    for t in itertools.product(*grids):
        yield t

@dataclass
class FCConfig:
    baseline_inputs: Dict[str, Any]
    fixed: Dict[str, Any]
    bounds: Dict[str, Tuple[float, float]]
    free: List[str]
    uncertain: List[str]
    method: str = "grid"  # grid|random
    n_per_dim: int = 5
    n_random: int = 200
    seed: int = 0
    feasible_only_export: bool = True

def _dominant(cs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "feasible": cs.get("feasible"),
        "worst_hard": cs.get("worst_hard"),
        "worst_hard_margin_frac": cs.get("worst_hard_margin_frac"),
        "hard_violations": cs.get("hard_violations"),
    }

def run_feasibility_completion(cfg: FCConfig) -> Dict[str, Any]:
    created = _created_utc()
    rng = random.Random(int(cfg.seed))

    # Build candidate points
    base_inputs = dict(cfg.baseline_inputs or {})
    base_inputs.update(cfg.fixed or {})
    vars_all = list(cfg.free) + list(cfg.uncertain)
    for v in vars_all:
        if v not in cfg.bounds:
            raise ValueError(f"missing bounds for {v}")

    points: List[Dict[str, Any]] = []
    if cfg.method == "grid":
        grids = [linspace(cfg.bounds[v][0], cfg.bounds[v][1], int(cfg.n_per_dim)) for v in vars_all]
        for vals in _product(grids):
            d = dict(base_inputs)
            for v,val in zip(vars_all, vals):
                d[v] = float(val)
            points.append(d)
    elif cfg.method == "random":
        for _ in range(int(cfg.n_random)):
            d = dict(base_inputs)
            for v in vars_all:
                lo,hi = cfg.bounds[v]
                d[v] = lo + (hi-lo)*rng.random()
            points.append(d)
    else:
        raise ValueError("method must be grid or random")

    evals=[]
    feasible_pts=[]
    dominant_counts={}
    for i, inp in enumerate(points):
        art = evaluate_point_inputs(inputs_dict=inp, solver_meta={"label":"fc_v133"})
        cs = art.get("constraints_summary", {}) if isinstance(art.get("constraints_summary"), dict) else {}
        outs = art.get("outputs", {}) if isinstance(art.get("outputs"), dict) else {}
        dom = _dominant(cs)
        worst = str(dom.get("worst_hard") or "")
        if worst:
            dominant_counts[worst] = dominant_counts.get(worst, 0) + 1

        rec = {
            "i": i,
            "inputs": inp,
            "feasible": dom.get("feasible"),
            "worst_hard": dom.get("worst_hard"),
            "worst_hard_margin_frac": dom.get("worst_hard_margin_frac"),
            "Q": outs.get("Q"),
            "Pfus_MW": outs.get("Pfus_MW"),
            "Pnet_MW": outs.get("Pnet_MW"),
        }
        evals.append(rec)
        if dom.get("feasible") is True:
            feasible_pts.append(rec)

    # envelope for free vars from feasible points
    envelope={}
    if feasible_pts:
        for v in vars_all:
            vals=[]
            for r in feasible_pts:
                x=r.get("inputs", {}).get(v)
                fx=_safe_float(x)
                if fx is not None:
                    vals.append(fx)
            if vals:
                envelope[v] = {"min": min(vals), "max": max(vals)}

    report={
        "kind":"shams_feasibility_completion_report",
        "version":"v133",
        "created_utc": created,
        "config": {
            "fixed": cfg.fixed,
            "baseline_inputs_sha256": _sha256((json.dumps(cfg.baseline_inputs, sort_keys=True, default=str) if isinstance(cfg.baseline_inputs, dict) else repr(cfg.baseline_inputs)).encode("utf-8")),
            "bounds": {k: [float(v[0]), float(v[1])] for k,v in cfg.bounds.items()},
            "free": list(cfg.free),
            "uncertain": list(cfg.uncertain),
            "method": cfg.method,
            "n_per_dim": int(cfg.n_per_dim),
            "n_random": int(cfg.n_random),
            "seed": int(cfg.seed),
        },
        "exists_feasible": bool(feasible_pts),
        "n_evals": len(evals),
        "n_feasible": len(feasible_pts),
        "dominant_constraint_counts": dominant_counts,
        "envelope": envelope,
        "evaluations_all": evals,
        "evaluations": (feasible_pts if cfg.feasible_only_export else evals),
    }
    return report

def build_fc_bundle_zip(report: Dict[str, Any]) -> Dict[str, Any]:
    created = str(report.get("created_utc") or _created_utc())

    # CSV of evaluations
    rows = list(report.get("evaluations") or [])
    fieldnames = ["i","feasible","worst_hard","worst_hard_margin_frac","Q","Pfus_MW","Pnet_MW"]
    # add var columns
    cfg = report.get("config", {}) if isinstance(report.get("config"), dict) else {}
    bounds = cfg.get("bounds", {}) if isinstance(cfg.get("bounds"), dict) else {}
    varcols = list(bounds.keys())
    fieldnames += [f"in_{v}" for v in varcols]

    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        inp = r.get("inputs", {}) if isinstance(r.get("inputs"), dict) else {}
        out = {k: r.get(k) for k in ["i","feasible","worst_hard","worst_hard_margin_frac","Q","Pfus_MW","Pnet_MW"]}
        for v in varcols:
            out[f"in_{v}"] = inp.get(v)
        w.writerow(out)
    csv_bytes = buf.getvalue().encode("utf-8")

    rep_bytes = json.dumps(report, indent=2, sort_keys=True).encode("utf-8")

    manifest = {
        "kind":"shams_fc_bundle_manifest",
        "version":"v133",
        "created_utc": created,
        "files": {
            "fc_report_v133.json": {"sha256": _sha256(rep_bytes), "bytes": len(rep_bytes)},
            "fc_table_v133.csv": {"sha256": _sha256(csv_bytes), "bytes": len(csv_bytes)},
        }
    }
    man_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fc_report_v133.json", rep_bytes)
        z.writestr("fc_table_v133.csv", csv_bytes)
        z.writestr("manifest_v133.json", man_bytes)

    return {"kind":"shams_fc_bundle", "version":"v133", "created_utc": created, "manifest": manifest, "zip_bytes": zbuf.getvalue()}
