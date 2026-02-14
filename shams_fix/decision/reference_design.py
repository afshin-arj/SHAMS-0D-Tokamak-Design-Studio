from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import math

def _get_kpi(art: Dict[str, Any], key: str, default: float = float("nan")) -> float:
    kpis = art.get("kpis", {}) if isinstance(art.get("kpis", {}), dict) else {}
    v = kpis.get(key, art.get("outputs", {}).get(key, default))
    try:
        return float(v)
    except Exception:
        return default

def _hard_feasible(art: Dict[str, Any]) -> bool:
    cons = art.get("constraints", [])
    ok = True
    for c in cons:
        if not isinstance(c, dict): 
            continue
        if str(c.get("severity","hard")).lower() != "hard":
            continue
        if not bool(c.get("passed", True)):
            ok = False
            break
    return ok

def synthesize_reference_design(artifacts: List[Dict[str, Any]], *, waive_decision_grade: bool = False) -> Optional[Dict[str, Any]]:
    """Choose a single recommended reference design from a set of run artifacts.

    Transparent rule set:
    1) Must pass all hard constraints.
    2) Must satisfy decision-grade conservative maturity unless waived.
    3) Rank by regret across a small objective set (min COE, max net power, max robustness).
       If objective values missing, fall back gracefully.

    Returns a dict with reference selection and rationale.
    """
    candidates = []
    for a in artifacts:
        if not isinstance(a, dict):
            continue
        if not _hard_feasible(a):
            continue
        decision = a.get("decision", {}) if isinstance(a.get("decision", {}), dict) else {}
        if not waive_decision_grade and decision.get("decision_grade_ok") is False:
            continue
        candidates.append(a)

    if not candidates:
        return None

    # Objective keys (simple and transparent)
    # Lower is better for COE; higher is better for net power; higher is better for robustness.
    vals = []
    for a in candidates:
        coe = _get_kpi(a, "COE_$MWh", _get_kpi(a, "coe_$MWh", float("nan")))
        pnet = _get_kpi(a, "P_e_net_MW", _get_kpi(a, "P_net_MW", float("nan")))
        prob = _get_kpi(a, "p_feasible", _get_kpi(a, "prob_feasible", float("nan")))
        mhm = _get_kpi(a, "min_hard_margin", float("nan"))
        vals.append((coe, pnet, prob, mhm))

    # Compute ideal and worst for normalization
    def finite(x): 
        return (x is not None) and (isinstance(x, (int,float))) and math.isfinite(float(x))

    coes=[v[0] for v in vals if finite(v[0])]
    pnets=[v[1] for v in vals if finite(v[1])]
    probs=[v[2] for v in vals if finite(v[2])]
    mhms=[v[3] for v in vals if finite(v[3])]

    # Defaults to avoid division by zero
    coe_min, coe_max = (min(coes), max(coes)) if coes else (1.0, 1.0)
    pnet_min, pnet_max = (min(pnets), max(pnets)) if pnets else (1.0, 1.0)
    prob_min, prob_max = (min(probs), max(probs)) if probs else (1.0, 1.0)
    mhm_min, mhm_max = (min(mhms), max(mhms)) if mhms else (0.0, 0.0)

    def norm(x, lo, hi):
        if not finite(x) or not finite(lo) or not finite(hi) or hi == lo:
            return 0.0
        return (float(x)-float(lo))/(float(hi)-float(lo))

    # Regret: distance from ideal (0 best). Weights are explicit and editable.
    W_COE=0.45
    W_PNET=0.25
    W_PROB=0.20
    W_MARGIN=0.10

    best_idx=0
    best_score=float("inf")
    scored=[]
    for i,a in enumerate(candidates):
        coe,pnet,prob,mhm = vals[i]
        # For COE, smaller is better: use (1 - norm)
        r_coe = 1.0 - norm(coe, coe_min, coe_max) if coes else 0.0
        # For benefits, larger is better: use (1 - norm(benefit))
        r_pnet = 1.0 - norm(pnet, pnet_min, pnet_max) if pnets else 0.0
        r_prob = 1.0 - norm(prob, prob_min, prob_max) if probs else 0.0
        r_mhm = 1.0 - norm(mhm, mhm_min, mhm_max) if mhms else 0.0

        score = W_COE*r_coe + W_PNET*r_pnet + W_PROB*r_prob + W_MARGIN*r_mhm
        scored.append((score, i))
        if score < best_score:
            best_score = score
            best_idx = i

    chosen = candidates[best_idx]
    meta = chosen.get("meta", {}) if isinstance(chosen.get("meta", {}), dict) else {}
    rid = meta.get("run_id", chosen.get("input_hash", f"candidate_{best_idx}"))

    return {
        "id": str(rid),
        "score": float(best_score),
        "weights": {"COE": W_COE, "P_e_net": W_PNET, "p_feasible": W_PROB, "min_hard_margin": W_MARGIN},
        "selected_from": len(candidates),
        "waive_decision_grade": bool(waive_decision_grade),
        "why_this_design": [
            "Passes all hard constraints",
            "Minimizes weighted regret across cost, net power, robustness, and margin"
        ],
        "artifact_path": chosen.get("_path", None),
    }
