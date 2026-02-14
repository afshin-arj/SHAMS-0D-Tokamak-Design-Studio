from __future__ import annotations
"""Feasibility Completion Evidence (v159)

Goal:
- Given a *partial* user specification (some known parameters) plus bounded unknowns,
  provide evidence that a feasible completion exists (or not found within budget),
  along with a best witness, bottleneck constraints, and minimal relaxation suggestions.

Safety:
- Downstream-only. Uses existing evaluator and constraint reporting.
- No physics changes, no solver logic changes.

Implementation strategy (v159):
- Monte Carlo or Latin-hypercube-like sampling over unknowns within user-provided bounds.
- Evaluate each candidate via tools.study_matrix.evaluate_point_inputs (stable path used by v156).
- Track best candidate (max min_margin), first feasible witness, and failure dominance stats.
- Suggest minimal relaxations from the best infeasible candidate's violations list (if available).

Schema:
kind: shams_feasibility_completion_evidence, version: v159
"""

from typing import Any, Dict, List, Tuple, Optional
import json, time, hashlib, math, copy, random
from pathlib import Path
from collections import defaultdict

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
    try:
        return _sha_obj(assumption_set)
    except Exception:
        return ""

def _min_margin_from_payload(payload: Dict[str, Any]) -> Tuple[float, str, List[Dict[str, Any]]]:
    # payload is shams_run_artifact payload
    cons = payload.get("constraints") or []
    best_m = float("inf")
    best_name = ""
    viols=[]
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
            if m < 0:
                viols.append({"name": nm, "margin": m, "value": c.get("value"), "limit": c.get("limit")})
    if best_m is float("inf"):
        return (float("nan"), "", [])
    viols.sort(key=lambda v: v.get("margin", 0.0))
    return (float(best_m), best_name, viols[:10])

def _status_from_margin(m: float, eps: float=1e-6) -> str:
    if not math.isfinite(m):
        return "unknown"
    if m >= eps:
        return "feasible"
    if m <= -eps:
        return "infeasible"
    return "marginal"

def build_feasibility_completion_evidence(
    *,
    known: Dict[str, Any],
    unknowns: List[Dict[str, Any]],
    fixed: Optional[List[Dict[str, Any]]] = None,
    assumption_set: Optional[Dict[str, Any]] = None,
    n_samples: int = 400,
    seed: int = 0,
    strategy: str = "random",
    margin_eps: float = 1e-6,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(known, dict) or not known:
        raise ValueError("known must be a non-empty dict")
    if not isinstance(unknowns, list) or not unknowns:
        raise ValueError("unknowns must be a non-empty list of {name,bounds}")

    fixed = fixed if isinstance(fixed, list) else []
    assumption_set = assumption_set if isinstance(assumption_set, dict) else {}
    policy = policy if isinstance(policy, dict) else {}
    rng=random.Random(int(seed))

    # Build override dict from fixed list
    fixed_over={}
    for f in fixed:
        if isinstance(f, dict) and f.get("name") is not None:
            fixed_over[str(f.get("name"))]=f.get("value")

    # Parse bounds
    vars=[]
    for u in unknowns:
        if not isinstance(u, dict):
            continue
        nm=str(u.get("name") or "")
        b=u.get("bounds")
        if not (nm and isinstance(b, (list,tuple)) and len(b)==2):
            continue
        lo=float(b[0]); hi=float(b[1])
        if hi<lo:
            lo,hi=hi,lo
        vars.append((nm, lo, hi))
    if not vars:
        raise ValueError("No valid unknowns parsed. Each unknown requires name and bounds [lo,hi].")

    # sampling helpers
    def sample_point(k: int) -> Dict[str, Any]:
        out={}
        if strategy=="lhs":
            # simple stratified per-dimension (not full LHS but stable)
            for nm,lo,hi in vars:
                t=(k + rng.random())/float(max(1,n_samples))
                out[nm]=lo + t*(hi-lo)
        else:
            for nm,lo,hi in vars:
                out[nm]=lo + rng.random()*(hi-lo)
        return out

    # Evaluate candidates
    dominance=defaultdict(int)
    near=defaultdict(int)
    best=None  # tuple(min_margin, payload, x_inputs)
    witness=None
    rows=[]
    for k in range(int(n_samples)):
        x = {}
        x.update(known)
        x.update(fixed_over)
        x.update(sample_point(k))
        # evaluate via stable v156 path
        payload = None
        try:
            payload = evaluate_point_inputs(inputs_dict=x, solver_meta={"label":"v159_completion", "assumption_set": assumption_set})
        except TypeError:
            # fallback variants for older signatures
            try:
                payload = evaluate_point_inputs(inputs_dict=x)
            except TypeError:
                payload = evaluate_point_inputs(x)
        if not (isinstance(payload, dict) and payload.get("kind")=="shams_run_artifact"):
            continue
        m, dom, viols = _min_margin_from_payload(payload)
        st=_status_from_margin(m, float(margin_eps))
        rows.append({"k":k, "min_margin": m, "status": st, "dominant_constraint": dom})
        if dom:
            dominance[dom]+=1
        if math.isfinite(m) and abs(m) <= 0.05 and dom:
            near[dom]+=1
        if (best is None) or (math.isfinite(m) and m > best[0]):
            best=(float(m), payload, x, dom, viols)
        if witness is None and st=="feasible":
            witness=(float(m), payload, x, dom, viols)

    verdict="inconclusive"
    if witness is not None:
        verdict="exists"
    elif best is not None and (best[0] < 0):
        verdict="does_not_exist" if policy.get("strict") else "inconclusive"

    # Minimal relaxations: use violations from best infeasible candidate as hints
    minimal_relax=[]
    bottleneck={}
    if best is not None:
        m_best, payload_best, x_best, dom_best, viols_best = best
        bottleneck={
            "dominant_constraint": dom_best,
            "reason": "dominant_violation_ranking",
            "sampled_best_margin": m_best,
            "dominance_ranked": [{"name":k, "count":int(v), "near_count": int(near.get(k,0))} for k,v in sorted(dominance.items(), key=lambda kv: kv[1], reverse=True)][:15],
        }
        for v in (viols_best or []):
            nm=str(v.get("name") or "")
            if not nm:
                continue
            # Suggest relaxing the associated assumption (if present) or limit; conservative delta is |margin|
            minimal_relax.append({
                "assumption": f"{nm}_limit",
                "delta": float(abs(float(v.get("margin") or 0.0))),
                "note": "Heuristic: relax limit by |margin| (units per constraint definition).",
            })
        minimal_relax = minimal_relax[:10]

    best_witness=None
    if witness is not None:
        m_w, payload_w, x_w, dom_w, viols_w = witness
        best_witness={
            "x": x_w,
            "min_constraint_margin": m_w,
            "dominant_constraint": dom_w,
        }
    elif best is not None:
        m_b, payload_b, x_b, dom_b, viols_b = best
        best_witness={
            "x": x_b,
            "min_constraint_margin": m_b,
            "dominant_constraint": dom_b,
        }

    out={
        "kind":"shams_feasibility_completion_evidence",
        "version":"v159",
        "issued_utc": _utc(),
        "shams_version": str((Path(__file__).resolve().parents[1]/"VERSION").read_text(encoding="utf-8").strip().splitlines()[0]),
        "study_id": str(policy.get("study_id") or ""),
        "provenance": {
            "generator": policy.get("generator","ui"),
            "strategy": str(strategy),
            "seed": int(seed),
            "budget": {"n_samples": int(n_samples)},
        },
        "assumptions": {"assumption_set": assumption_set, "assumption_sha256": _assumption_sha(assumption_set)},
        "integrity": {"object_sha256": ""},
        "payload": {
            "query": {
                "known": known,
                "unknowns": [{"name":nm, "bounds":[lo,hi]} for nm,lo,hi in vars],
                "fixed": fixed,
            },
            "result": {
                "verdict": verdict,
                "best_witness": best_witness,
                "bottleneck": bottleneck,
                "minimal_relaxations": minimal_relax,
            },
            "evidence": {
                "method": "sampling_search",
                "n_evaluated": int(len(rows)),
                "rows_preview": rows[:200],
            },
        },
    }
    tmp=copy.deepcopy(out); tmp["integrity"]={"object_sha256": ""}
    out["integrity"]["object_sha256"]=_sha_obj(tmp)
    return out
