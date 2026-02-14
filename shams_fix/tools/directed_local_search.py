from __future__ import annotations
"""Directed Local Search (v162)

Purpose:
- Fast, sandboxed local search to reach feasibility starting from a baseline guess.
- Complements v159 (existence evidence) and v161 (frontier) with a directed improvement walk.

Safety / invariants:
- Downstream-only; uses existing evaluator (tools.study_matrix.evaluate_point_inputs).
- No physics changes, no solver logic changes.
- Hard evaluation budget + bounded variables.

Method (v162):
- Coordinate hill-climb on a chosen set of decision variables with bounds.
- Step size starts as a fraction of bound range; shrinks when no progress.
- Accept the best improving move among +/- step across all variables per iteration.
- Stops when feasible, budget used, or step below minimum.

Artifact:
kind: shams_directed_local_search, version: v162
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
            x0v=(lo+hi)/2.0
        # clamp baseline
        x0v=max(lo, min(hi, x0v))
        out.append((nm, lo, hi, x0v))
    if not out:
        raise ValueError("No valid decision variables; each requires name and bounds [lo,hi].")
    return out

def _apply_bounds(x: Dict[str, Any], vars: List[Tuple[str,float,float,float]]) -> Dict[str, Any]:
    out=dict(x)
    for nm,lo,hi,_ in vars:
        try:
            v=float(out.get(nm))
        except Exception:
            v=(lo+hi)/2.0
        out[nm]=max(lo, min(hi, v))
    return out

def _dist_l2(x: Dict[str, Any], vars: List[Tuple[str,float,float,float]]) -> float:
    s2=0.0
    for nm,lo,hi,x0v in vars:
        den=(hi-lo) if (hi-lo)!=0 else 1.0
        try:
            xv=float(x.get(nm))
        except Exception:
            xv=x0v
        dn=(xv-x0v)/den
        s2 += dn*dn
    return float(math.sqrt(s2))

def build_directed_local_search(
    *,
    baseline: Dict[str, Any],
    decision_vars: List[Dict[str, Any]],
    fixed: Optional[List[Dict[str, Any]]] = None,
    assumption_set: Optional[Dict[str, Any]] = None,
    max_evals: int = 200,
    seed: int = 0,
    initial_step_norm: float = 0.12,
    min_step_norm: float = 0.004,
    step_shrink: float = 0.5,
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

    # starting point
    x=dict(baseline)
    x.update(fixed_over)
    for nm,_,__,x0v in vars:
        x[nm]=x0v
    x=_apply_bounds(x, vars)

    history=[]
    n_eval=0

    def eval_x(xcand: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], float, str, str]:
        nonlocal n_eval
        if n_eval >= int(max_evals):
            return (None, float("nan"), "", "budget_exhausted")
        payload=None
        try:
            payload = evaluate_point_inputs(inputs_dict=xcand, solver_meta={"label":"v162_local_search", "assumption_set": assumption_set})
        except TypeError:
            try:
                payload = evaluate_point_inputs(inputs_dict=xcand)
            except TypeError:
                payload = evaluate_point_inputs(xcand)
        n_eval += 1
        if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
            return (payload, float("nan"), "", "invalid_payload")
        m, dom = _min_margin_from_payload(payload)
        st=_status(m, float(margin_eps))
        return (payload, float(m), str(dom), st)

    payload0, m0, dom0, st0 = eval_x(x)
    history.append({
        "eval": int(n_eval),
        "x_decision": {nm: float(x.get(nm)) for nm,_,__,___ in vars},
        "min_margin": m0 if math.isfinite(m0) else None,
        "status": st0,
        "dominant_constraint": dom0,
        "distance_l2": _dist_l2(x, vars),
        "note": "start",
    })

    best_x=dict(x)
    best_payload=payload0
    best_m=m0
    best_dom=dom0
    best_st=st0

    step=float(initial_step_norm)
    stop_reason="budget_exhausted" if (n_eval>=max_evals) else ""

    # coordinate search loop
    while n_eval < int(max_evals):
        if best_st=="feasible":
            stop_reason="feasible_found"
            break
        if step < float(min_step_norm):
            stop_reason="step_too_small"
            break

        # explore moves
        cand_best=None  # (m, x, dom, st, nm, direction)
        for nm,lo,hi,x0v in vars:
            span=(hi-lo) if (hi-lo)!=0 else 1.0
            delta=step*span
            for sgn in (+1.0, -1.0):
                x2=dict(best_x)
                try:
                    x2v=float(x2.get(nm))
                except Exception:
                    x2v=x0v
                x2[nm]=x2v + sgn*delta
                x2=_apply_bounds(x2, vars)
                payload2, m2, dom2, st2 = eval_x(x2)
                if not math.isfinite(m2):
                    continue
                # accept strict improvement in min_margin
                if (cand_best is None) or (m2 > cand_best[0]):
                    cand_best=(float(m2), x2, dom2, st2, nm, ("+" if sgn>0 else "-"))

                if n_eval >= int(max_evals):
                    break
            if n_eval >= int(max_evals):
                break

        if cand_best is None:
            # no evaluable candidate (shouldn't happen), shrink
            step *= float(step_shrink)
            history.append({
                "eval": int(n_eval),
                "x_decision": {nm: float(best_x.get(nm)) for nm,_,__,___ in vars},
                "min_margin": best_m if math.isfinite(best_m) else None,
                "status": best_st,
                "dominant_constraint": best_dom,
                "distance_l2": _dist_l2(best_x, vars),
                "note": "no_candidates_shrink",
                "step_norm": step,
            })
            continue

        m2, x2, dom2, st2, var_nm, var_dir = cand_best
        if (math.isfinite(best_m) and m2 > best_m) or (not math.isfinite(best_m) and math.isfinite(m2)):
            best_x=dict(x2)
            best_m=float(m2)
            best_dom=str(dom2)
            best_st=str(st2)
            history.append({
                "eval": int(n_eval),
                "x_decision": {nm: float(best_x.get(nm)) for nm,_,__,___ in vars},
                "min_margin": best_m,
                "status": best_st,
                "dominant_constraint": best_dom,
                "distance_l2": _dist_l2(best_x, vars),
                "note": f"accept {var_nm}{var_dir} step",
                "step_norm": step,
            })
            # small random jitter for tie-breaking (bounded) if still infeasible and step is large
            if best_st!="feasible" and step > (min_step_norm*2):
                if rng.random() < 0.15 and n_eval < int(max_evals):
                    jnm,lo,hi,x0v = rng.choice(vars)
                    span=(hi-lo) if (hi-lo)!=0 else 1.0
                    jdelta = (rng.random()*2-1)*0.25*step*span
                    xj=dict(best_x)
                    xj[jnm]=float(xj.get(jnm, x0v)) + jdelta
                    xj=_apply_bounds(xj, vars)
                    payloadj, mj, domj, stj = eval_x(xj)
                    if math.isfinite(mj) and mj >= best_m:
                        best_x=dict(xj); best_m=float(mj); best_dom=str(domj); best_st=str(stj)
                        history.append({
                            "eval": int(n_eval),
                            "x_decision": {nm: float(best_x.get(nm)) for nm,_,__,___ in vars},
                            "min_margin": best_m,
                            "status": best_st,
                            "dominant_constraint": best_dom,
                            "distance_l2": _dist_l2(best_x, vars),
                            "note": f"jitter {jnm}",
                            "step_norm": step,
                        })
        else:
            # no improvement at this step -> shrink
            step *= float(step_shrink)
            history.append({
                "eval": int(n_eval),
                "x_decision": {nm: float(best_x.get(nm)) for nm,_,__,___ in vars},
                "min_margin": best_m if math.isfinite(best_m) else None,
                "status": best_st,
                "dominant_constraint": best_dom,
                "distance_l2": _dist_l2(best_x, vars),
                "note": "no_improvement_shrink",
                "step_norm": step,
            })

    if not stop_reason:
        stop_reason="budget_exhausted"

    result={
        "stop_reason": stop_reason,
        "n_evals": int(n_eval),
        "final": {
            "status": best_st,
            "min_margin": best_m if math.isfinite(best_m) else None,
            "dominant_constraint": best_dom,
            "x_decision": {nm: float(best_x.get(nm)) for nm,_,__,___ in vars},
            "distance_l2": _dist_l2(best_x, vars),
        },
        "history": history[:600],
    }

    out={
        "kind":"shams_directed_local_search",
        "version":"v162",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(policy.get("study_id") or ""),
        "provenance": {
            "generator": policy.get("generator","ui"),
            "seed": int(seed),
            "budget": {"max_evals": int(max_evals)},
            "step": {"initial_norm": float(initial_step_norm), "min_norm": float(min_step_norm), "shrink": float(step_shrink)},
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
        },
    }
    tmp=copy.deepcopy(out); tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out
