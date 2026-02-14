from __future__ import annotations
"""Parameter Guidance (v135)

Safe, explicit heuristics to help non-expert users choose FREE variables and bounds
for Feasibility Completion (v133+).

No physics/solver interaction. Pure heuristics + sanity bounds.
"""

from typing import Any, Dict, List, Tuple, Optional
import math

# Conservative global sanity bounds for common tokamak-ish parameters.
# These are intentionally broad and must be treated as "guardrails", not truth.
GLOBAL_SANITY = {
    "R0_m": (0.5, 20.0),
    "a_m": (0.1, 8.0),
    "Bt_T": (0.1, 25.0),
    "Ip_MA": (0.1, 50.0),
    "kappa": (1.0, 3.0),
    "q95": (1.5, 8.0),
    "beta_N": (0.2, 6.0),
    "f_GW": (0.1, 1.6),
}

DEFAULT_PCT = {
    "Ip_MA": 0.30,
    "kappa": 0.15,
    "q95": 0.25,
    "a_m": 0.20,
    "beta_N": 0.30,
    "f_GW": 0.20,
    "Bt_T": 0.15,
    "R0_m": 0.15,
}

PREFERRED_FREE_ORDER = ["Ip_MA", "kappa", "q95", "a_m", "beta_N", "f_GW"]

def suggest_free_vars(available: List[str], fixed: List[str], max_k: int = 3) -> List[str]:
    cand = [v for v in PREFERRED_FREE_ORDER if v in available and v not in fixed]
    # fill with any other numeric levers
    for v in available:
        if v not in fixed and v not in cand:
            cand.append(v)
    return cand[:max(1, int(max_k))]

def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def suggest_bounds(base_inputs: Dict[str, Any], var: str) -> Tuple[float, float]:
    v0 = base_inputs.get(var)
    try:
        v0f = float(v0)
    except Exception:
        v0f = None

    # percent-based default
    pct = float(DEFAULT_PCT.get(var, 0.20))
    if v0f is None or abs(v0f) < 1e-12:
        # fallback symmetric
        lo, hi = (-1.0, 1.0)
        if var in GLOBAL_SANITY:
            lo, hi = GLOBAL_SANITY[var]
        return float(lo), float(hi)

    lo = v0f * (1.0 - pct)
    hi = v0f * (1.0 + pct)

    if var in GLOBAL_SANITY:
        s_lo, s_hi = GLOBAL_SANITY[var]
        lo = _clip(lo, s_lo, s_hi)
        hi = _clip(hi, s_lo, s_hi)
        if lo >= hi:
            lo, hi = s_lo, s_hi
    return float(lo), float(hi)

def sanity_check_bounds(var: str, lo: float, hi: float) -> List[str]:
    msgs=[]
    if lo >= hi:
        msgs.append("min >= max")
    if var in GLOBAL_SANITY:
        s_lo, s_hi = GLOBAL_SANITY[var]
        if lo < s_lo or hi > s_hi:
            msgs.append(f"outside broad sanity [{s_lo}, {s_hi}]")
    # generic guards
    if not (math.isfinite(lo) and math.isfinite(hi)):
        msgs.append("non-finite bound")
    return msgs
