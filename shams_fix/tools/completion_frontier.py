from __future__ import annotations
"""Completion Frontier + Minimal Change Distance (v161)

Purpose:
- Quantify how far a partial design is from feasibility under bounded unknowns.
- Provide a *minimal change* witness: the closest feasible completion found to a baseline guess.
- Provide a Pareto frontier between feasibility margin and change distance.

Safety:
- Downstream-only. Uses existing evaluator via tools.study_matrix.evaluate_point_inputs.
- No physics changes, no solver logic changes.

Method (v161):
- Define a baseline vector x0 (baseline inputs).
- Choose decision variables (subset of inputs) with bounds.
- Sample candidates (random or lhs).
- Evaluate each candidate -> min_constraint_margin.
- Compute normalized L2 distance in decision variable space:
    d = sqrt(sum(((x_i - x0_i)/(hi-lo))^2))
  and L1 distance as auxiliary.
- Frontier: keep non-dominated candidates in (d, -margin) (minimize distance, maximize margin).
- Minimal-change feasible witness: feasible candidate with smallest d.
"""

from typing import Any, Dict, List, Tuple, Optional
import json, time, hashlib, math, copy, random
from pathlib import Path

from tools.study_matrix import evaluate_point_inputs

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _canon_json(o: Any) -> bytes:
    return json.dumps(o, indent=2, sort_keys=True, default=str).encode("utf-8")

def _sha_bytes(b: bytes) -> str:
    h=hashlib.sha256(); h.update(b); return h.hexdigest()

def _sha_obj(o: Any) -> str:
    return _sha_bytes(_canon_json(o))

def _min_margin_from_payload(payload: Dict[str, Any]) -> Tuple[float, str]:
    cons = payload.get("constraints") or []
    best_m = float("inf")
    best_name = ""
    if isinstance(cons, list):
        for c in cons:
            if not isinstance(c, dict):
                continue
            try:
                m=float(c.get("margin"))
            except Exception:
                continue
            nm=str(c.get("name") or "")
            if m < best_m:
                best_m = m
                best_name = nm
    if best_m is float("inf"):
        return (float("nan"), "")
    return (float(best_m), best_name)

def _status(m: float, eps: float=1e-6) -> str:
    if not math.isfinite(m):
        return "unknown"
    if m >= eps:
        return "feasible"
    if m <= -eps:
        return "infeasible"
    return "marginal"

def _parse_vars(vars_spec: List[Dict[str, Any]], x0: Dict[str, Any]) -> List[Tuple[str,float,float,float]]:
    out=[]
    for v in (vars_spec or []):
        if not isinstance(v, dict):
            continue
        nm=str(v.get("name") or "")
        b=v.get("bounds")
        if not (nm and isinstance(b,(list,tuple)) and len(b)==2):
            continue
        lo=float(b[0]); hi=float(b[1])
        if hi<lo: lo,hi=hi,lo
        try:
            x0v=float(x0.get(nm))
        except Exception:
            # if baseline missing, set midpoint
            x0v=(lo+hi)/2.0
        out.append((nm, lo, hi, x0v))
    if not out:
        raise ValueError("No valid decision variables; each requires name and bounds [lo,hi].")
    return out

def _dist(x: Dict[str, Any], vars: List[Tuple[str,float,float,float]]) -> Dict[str, float]:
    s2=0.0; s1=0.0
    for nm,lo,hi,x0v in vars:
        den=(hi-lo) if (hi-lo)!=0 else 1.0
        try:
            xv=float(x.get(nm))
        except Exception:
            xv=x0v
        dn=abs((xv-x0v)/den)
        s1 += dn
        s2 += dn*dn
    return {"l2": float(math.sqrt(s2)), "l1": float(s1)}

def _sample_point(k: int, n: int, rng: random.Random, vars: List[Tuple[str,float,float,float]], strategy: str) -> Dict[str, float]:
    x={}
    if strategy=="lhs":
        for nm,lo,hi,_ in vars:
            t=(k + rng.random())/float(max(1,n))
            x[nm]=lo + t*(hi-lo)
    else:
        for nm,lo,hi,_ in vars:
            x[nm]=lo + rng.random()*(hi-lo)
    return x

def _pareto_front(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # minimize distance.l2, maximize min_margin
    # keep non-dominated: no other row with d<= and margin>= with at least one strict
    front=[]
    for r in rows:
        d=r.get("distance_l2")
        m=r.get("min_margin")
        if not (isinstance(d,(int,float)) and isinstance(m,(int,float)) and math.isfinite(d) and math.isfinite(m)):
            continue
        dominated=False
        for q in rows:
            if q is r:
                continue
            d2=q.get("distance_l2"); m2=q.get("min_margin")
            if not (isinstance(d2,(int,float)) and isinstance(m2,(int,float)) and math.isfinite(d2) and math.isfinite(m2)):
                continue
            if (d2 <= d and m2 >= m) and (d2 < d or m2 > m):
                dominated=True
                break
        if not dominated:
            front.append(r)
    # sort by distance
    front.sort(key=lambda r: float(r.get("distance_l2", 1e9)))
    return front[:300]

def build_completion_frontier(
    *,
    baseline: Dict[str, Any],
    decision_vars: List[Dict[str, Any]],
    fixed: Optional[List[Dict[str, Any]]] = None,
    assumption_set: Optional[Dict[str, Any]] = None,
    n_samples: int = 800,
    seed: int = 0,
    strategy: str = "random",
    margin_eps: float = 1e-6,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(baseline, dict) or not baseline:
        raise ValueError("baseline must be a non-empty dict")
    fixed = fixed if isinstance(fixed, list) else []
    assumption_set = assumption_set if isinstance(assumption_set, dict) else {}
    policy = policy if isinstance(policy, dict) else {}
    rng=random.Random(int(seed))

    vars=_parse_vars(decision_vars, baseline)
    fixed_over={}
    for f in fixed:
        if isinstance(f, dict) and f.get("name") is not None:
            fixed_over[str(f.get("name"))]=f.get("value")

    rows=[]
    best_feas=None  # (d, row)
    best_margin=None  # max margin regardless
    for k in range(int(n_samples)):
        x=dict(baseline)
        x.update(fixed_over)
        x.update(_sample_point(k, int(n_samples), rng, vars, str(strategy)))
        # evaluate via stable v156 path
        payload = None
        try:
            payload = evaluate_point_inputs(inputs_dict=x, solver_meta={"label":"v161_frontier", "assumption_set": assumption_set})
        except TypeError:
            try:
                payload = evaluate_point_inputs(inputs_dict=x)
            except TypeError:
                payload = evaluate_point_inputs(x)
        if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
            continue
        m, dom = _min_margin_from_payload(payload)
        st=_status(m, float(margin_eps))
        dist=_dist(x, vars)
        row={
            "k": int(k),
            "status": st,
            "min_margin": float(m) if math.isfinite(m) else None,
            "dominant_constraint": dom,
            "distance_l2": dist["l2"],
            "distance_l1": dist["l1"],
            "x_decision": {nm: float(x.get(nm)) for nm,_,__,___ in vars},
        }
        rows.append(row)
        if math.isfinite(m):
            if (best_margin is None) or (m > best_margin[0]):
                best_margin=(float(m), row)
        if st=="feasible":
            if (best_feas is None) or (row["distance_l2"] < best_feas[0]):
                best_feas=(float(row["distance_l2"]), row)

    front=_pareto_front(rows)
    result={
        "minimal_change_feasible": best_feas[1] if best_feas else None,
        "best_margin": best_margin[1] if best_margin else None,
        "frontier": front,
    }

    out={
        "kind":"shams_completion_frontier",
        "version":"v161",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(policy.get("study_id") or ""),
        "provenance": {
            "generator": policy.get("generator","ui"),
            "strategy": str(strategy),
            "seed": int(seed),
            "budget": {"n_samples": int(n_samples)},
            "distance_norm": "normalized_by_bounds",
        },
        "assumptions": {"assumption_set": assumption_set},
        "integrity": {"object_sha256": ""},
        "payload": {
            "query": {
                "baseline": baseline,
                "decision_vars": [{"name":nm, "bounds":[lo,hi], "baseline": x0v} for nm,lo,hi,x0v in vars],
                "fixed": fixed,
            },
            "result": result,
            "evidence": {
                "n_evaluated": int(len(rows)),
                "rows_preview": rows[:250],
            },
        },
    }
    tmp=copy.deepcopy(out); tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out
