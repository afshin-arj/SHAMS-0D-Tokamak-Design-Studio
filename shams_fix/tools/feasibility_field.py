from __future__ import annotations
"""Feasibility Field Engine (v156)

Downstream-only:
- Uses existing point evaluator + constraints + build_run_artifact.
- Produces a feasibility field artifact suitable for atlases and later boundary extraction.

Schema:
kind: shams_feasibility_field, version: v156
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from io import BytesIO, StringIO
import json, time, hashlib, csv, zipfile, math, copy

from tools.study_matrix import evaluate_point_inputs

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _assumption_sha(assumption_set: Dict[str, Any]) -> str:
    return _sha_obj(assumption_set if isinstance(assumption_set, dict) else {})

def _extract_margins(run_artifact: Dict[str, Any]) -> Tuple[float, str, List[Dict[str, Any]]]:
    cons = run_artifact.get("constraints", [])
    if not isinstance(cons, list):
        return (float("nan"), "", [])
    rows=[]
    min_margin=math.inf
    dom=""
    for c in cons:
        if not isinstance(c, dict):
            continue
        m=c.get("margin")
        try:
            mf=float(m)
        except Exception:
            continue
        rows.append({
            "name": c.get("name"),
            "value": c.get("value"),
            "limit": c.get("limit"),
            "sense": c.get("sense"),
            "margin": mf,
        })
        if mf < min_margin:
            min_margin=mf
            dom=str(c.get("name") or "")
    if min_margin is math.inf:
        min_margin=float("nan")
    # violations only
    viol=[r for r in rows if isinstance(r.get("margin"), (int,float)) and float(r["margin"]) < 0.0]
    # sort by most negative first
    viol.sort(key=lambda r: float(r.get("margin", 0.0)))
    return (float(min_margin), dom, viol[:6])

def _status_from_art(run_artifact: Dict[str, Any], margin_eps: float = 1e-6) -> str:
    # Prefer explicit feasibility flags if present; otherwise use margin.
    if isinstance(run_artifact.get("hard_feasible"), bool):
        hf=bool(run_artifact.get("hard_feasible"))
        if hf:
            return "feasible"
    mm, _, _ = _extract_margins(run_artifact)
    if not math.isfinite(mm):
        return "infeasible"
    if mm >= margin_eps:
        return "feasible"
    if abs(mm) < max(margin_eps, 1e-3):
        return "marginal"
    return "infeasible"

def build_feasibility_field(
    *,
    baseline_inputs: Dict[str, Any],
    axis1: Dict[str, Any],
    axis2: Dict[str, Any],
    fixed: Optional[List[Dict[str, Any]]] = None,
    assumption_set: Optional[Dict[str, Any]] = None,
    sampling: Optional[Dict[str, Any]] = None,
    solver_meta: Optional[Dict[str, Any]] = None,
    margin_eps: float = 1e-6,
) -> Dict[str, Any]:
    """Return dict with {field, zip_bytes, csv_bytes}."""
    fixed = fixed or []
    sampling = sampling or {}
    assumption_set = assumption_set or {}
    solver_meta = solver_meta or {"label":"feasibility_field_v156"}

    # axis grids
    def _grid(ax: Dict[str, Any]) -> List[float]:
        g=(ax.get("grid") or {})
        typ=str(g.get("type") or "linspace")
        if typ != "linspace":
            raise ValueError("Only linspace supported in v156")
        start=float(g.get("start"))
        stop=float(g.get("stop"))
        n=int(g.get("n"))
        if n < 2:
            return [start]
        step=(stop-start)/(n-1)
        return [start + i*step for i in range(n)]

    a1_name=str(axis1.get("name"))
    a2_name=str(axis2.get("name"))
    g1=_grid(axis1); g2=_grid(axis2)

    base=copy.deepcopy(baseline_inputs if isinstance(baseline_inputs, dict) else {})
    for f in fixed:
        if isinstance(f, dict) and f.get("name") is not None:
            base[str(f["name"])] = f.get("value")

    pts=[]
    dom_counts={}
    n_total=len(g1)*len(g2)
    t0=time.perf_counter()
    idx=0
    for v1 in g1:
        for v2 in g2:
            idx += 1
            d=copy.deepcopy(base)
            d[a1_name]=v1
            d[a2_name]=v2
            art = evaluate_point_inputs(inputs_dict=d, solver_meta=solver_meta)
            mm, dom, viol = _extract_margins(art)
            st = _status_from_art(art, margin_eps=margin_eps)
            dom_counts[dom]=dom_counts.get(dom,0)+1 if dom else dom_counts.get(dom,0)
            pts.append({
                "x": {a1_name: v1, a2_name: v2, **{k:v for k,v in d.items() if k not in (a1_name,a2_name)} },
                "status": st,
                "margin": {
                    "min_constraint_margin": mm,
                    "dominant_constraint": dom,
                    "violations": viol,
                },
                "diagnostics": {
                    "termination": str((art.get("meta") or {}).get("termination") or "unknown"),
                    "eval_ms": float((art.get("meta") or {}).get("eval_ms") or 0.0),
                    "solver_iters": int((art.get("meta") or {}).get("iters") or 0),
                },
                "artifact_ref": {
                    "kind":"shams_run_artifact",
                    "run_id": str(art.get("id") or ""),
                    "sha256": _sha_obj(art),
                },
            })

    elapsed=time.perf_counter()-t0
    feas=sum(1 for p in pts if p.get("status")=="feasible")
    summ={
        "feasible_fraction": (feas/float(n_total)) if n_total else 0.0,
        "n_points": n_total,
        "wall_time_s": float(elapsed),
        "dominant_constraints_ranked": [
            {"name": k, "count": int(v)} for k,v in sorted(dom_counts.items(), key=lambda kv: kv[1], reverse=True) if k
        ][:12],
    }

    field={
        "kind":"shams_feasibility_field",
        "version":"v156",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(sampling.get("study_id") or ""),
        "provenance": {
            "generator": str(sampling.get("generator") or "ui"),
            "solver": solver_meta or {},
        },
        "assumptions": {
            "assumption_set": assumption_set,
            "assumption_sha256": _assumption_sha(assumption_set),
        },
        "integrity": {
            "object_sha256": "",  # filled below
        },
        "payload": {
            "domain": {
                "parameters": [axis1, axis2],
                "fixed": fixed,
            },
            "sampling": {
                "strategy": str(sampling.get("strategy") or "grid"),
                "n_points": n_total,
                "seed": int(sampling.get("seed") or 0),
                "parallel": sampling.get("parallel") or {"enabled": False},
            },
            "field": {
                "points": pts,
                "summaries": summ,
            },
        },
    }
    # object sha excluding integrity field
    tmp=copy.deepcopy(field)
    tmp["integrity"]={"object_sha256": ""}
    field["integrity"]["object_sha256"]=_sha_obj(tmp)

    # CSV export (axes + status + min_margin + dominant)
    out=StringIO()
    w=csv.writer(out)
    w.writerow([a1_name, a2_name, "status", "min_constraint_margin", "dominant_constraint"])
    for p in pts:
        mm=p.get("margin",{}).get("min_constraint_margin")
        w.writerow([p["x"].get(a1_name), p["x"].get(a2_name), p.get("status"), mm, p.get("margin",{}).get("dominant_constraint")])
    csv_bytes=out.getvalue().encode("utf-8")

    # Bundle zip
    zbuf=BytesIO()
    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("feasibility_field_v156.json", _canon_json(field))
        z.writestr("feasibility_field_v156.csv", csv_bytes)
    return {"field": field, "zip_bytes": zbuf.getvalue(), "csv_bytes": csv_bytes}

