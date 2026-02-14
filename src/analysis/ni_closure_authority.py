"""
Non-Inductive Closure Authority (deterministic, post-processing only)

This module provides a governance-grade closure check for steady-state/hybrid claims.
No solvers, no iteration. Uses already-emitted artifact terms.

Author: © 2026 Afshin Arjhangmehr
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from pathlib import Path

def _is_finite(x: Any) -> bool:
    try:
        xf = float(x)
        return xf == xf and abs(xf) < 1.0e300
    except Exception:
        return False

def _f(x: Any, default: float=float("nan")) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _margin_frac(value: float, lim: float, sense: str) -> float:
    """
    Signed fractional margin. sense:
      - 'le': pass if value <= lim -> (lim - value)/max(|lim|,eps)
      - 'ge': pass if value >= lim -> (value - lim)/max(|lim|,eps)
    """
    eps = 1e-12
    den = max(abs(lim), eps)
    if sense == "le":
        return (lim - value) / den
    if sense == "ge":
        return (value - lim) / den
    raise ValueError("sense must be 'le' or 'ge'")

def evaluate_ni_closure_authority(out: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict of NI closure outputs (keys prefixed 'ni_...').
    Failure-safe: if required terms missing, returns UNKNOWN.
    """
    req = contract.get("required_terms", [])
    missing = [k for k in req if k not in out or not _is_finite(out.get(k))]
    fragile_thr = float(contract.get("fragile_margin_frac", 0.05))
    if missing:
        return {
            "ni_closure_regime": "unknown",
            "ni_fragility_class": "UNKNOWN",
            "ni_min_margin_frac": float("nan"),
            "ni_top_limiter": "missing_terms",
            "ni_missing_terms": missing,
        }

    Ip = _f(out["Ip_MA"])
    Icd = _f(out.get("I_cd_MA", out.get("I_cd_MA", float("nan"))))
    fbs = _f(out.get("profile_f_bootstrap_proxy"))
    if not _is_finite(fbs):
        fbs = float("nan")
    Ibs = fbs * Ip if _is_finite(fbs) else float("nan")
    fNI = (Icd + Ibs) / Ip if _is_finite(Icd) and _is_finite(Ibs) and _is_finite(Ip) and Ip > 0 else float("nan")

    # Choose regime based on fNI against contract bins
    regimes = contract.get("regimes", {})
    regime = "unknown"
    for name, r in regimes.items():
        mn = float(r.get("f_NI_min", -1e9))
        mx = float(r.get("f_NI_max", 1e9))
        if _is_finite(fNI) and (fNI >= mn) and (fNI <= mx):
            regime = name
            break

    # Margin for being inside chosen regime bin: min of (fNI - min), (max - fNI) normalized by max(|max|,eps)
    margins: List[Tuple[str, float]] = []

    if regime in regimes and _is_finite(fNI):
        mn = float(regimes[regime].get("f_NI_min", 0.0))
        mx = float(regimes[regime].get("f_NI_max", 1.0))
        # Use two ge/le margins then take min
        m1 = _margin_frac(fNI, mn, "ge")
        m2 = _margin_frac(fNI, mx, "le")
        margins.append(("ni_fNI_min_margin_frac", m1))
        margins.append(("ni_fNI_max_margin_frac", m2))
    else:
        margins.append(("ni_fNI_bin_margin_frac", float("nan")))

    # Current closure consistency: for steady_state we require fNI close to 1 within delta_I_frac_max
    delta_I = float(contract.get("delta_I_frac_max", 0.05))
    if _is_finite(fNI):
        if regime == "steady_state":
            err = abs(1.0 - fNI)
            mI = (delta_I - err) / max(delta_I, 1e-12)
        else:
            # For inductive/hybrid, closure is satisfied by definition; use bin margins only.
            mI = float("nan")
        margins.append(("ni_current_balance_margin_frac", mI))

    # Power closure: total auxiliary electric <= cap
    Paux_el = _f(out.get("P_aux_total_el_MW"))
    Paux_max = _f(out.get("P_aux_max_MW"))
    if _is_finite(Paux_el) and _is_finite(Paux_max):
        mP = _margin_frac(Paux_el, Paux_max, "le")
    else:
        mP = float("nan")
    margins.append(("ni_power_balance_margin_frac", mP))

    # Aggregate
    finite_margins = [(k,v) for k,v in margins if _is_finite(v)]
    if finite_margins:
        min_key, min_val = min(finite_margins, key=lambda kv: kv[1])
    else:
        min_key, min_val = ("ni_min_margin_frac", float("nan"))

    frag = "UNKNOWN"
    if _is_finite(min_val):
        if min_val < 0:
            frag = "INFEASIBLE"
        elif min_val < fragile_thr:
            frag = "FRAGILE"
        else:
            frag = "FEASIBLE"

    outd: Dict[str, Any] = {
        "ni_closure_regime": regime,
        "ni_fragility_class": frag,
        "ni_min_margin_frac": min_val,
        "ni_top_limiter": min_key,
        "ni_fNI": fNI,
        "ni_Ibs_MA_proxy": Ibs,
        "ni_Icd_MA": Icd,
        "ni_Ip_MA": Ip,
        "ni_P_aux_total_el_MW": Paux_el,
        "ni_P_aux_max_MW": Paux_max,
    }
    for k,v in margins:
        outd[k]=v
    return outd
