from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Robustness thresholds are expressed in terms of min_signed_margin.
# These are UI-facing defaults and can be overridden by callers.
DEFAULT_THRESHOLDS = {
    "near_feasible": 0.02,   # |margin| below this is "near"
    "fragile": 0.02,         # feasible but margin < fragile -> fragile
    "balanced": 0.10,        # feasible and margin < balanced -> balanced
    # robust: margin >= balanced
}

def _first_failure(constraints: List[Dict[str, Any]]) -> Optional[str]:
    worst = None
    worst_sm = None
    for r in constraints or []:
        try:
            sm = float(r.get("signed_margin"))
        except Exception:
            continue
        if worst_sm is None or sm < worst_sm:
            worst_sm = sm
            worst = str(r.get("name") or r.get("constraint") or "")
    return worst or None

def robustness_class(min_signed_margin: float, *, thresholds: Dict[str, float] = DEFAULT_THRESHOLDS) -> str:
    try:
        m = float(min_signed_margin)
    except Exception:
        return "unknown"
    if m < 0:
        return "infeasible"
    if m < float(thresholds.get("fragile", 0.02)):
        return "fragile"
    if m < float(thresholds.get("balanced", 0.10)):
        return "balanced"
    return "robust"

def feasibility_state(
    feasible: bool,
    min_signed_margin: float,
    *,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
    dominant: bool = False,
) -> str:
    try:
        m = float(min_signed_margin)
    except Exception:
        m = float("nan")

    near = float(thresholds.get("near_feasible", 0.02))
    if not feasible:
        if m != m:
            return "infeasible"
        return "near_feasible" if (-near <= m < 0) else "infeasible"

    rc = robustness_class(m, thresholds=thresholds)
    if dominant:
        return "feasible_dominant"
    if rc == "fragile":
        return "feasible_fragile"
    if rc == "balanced":
        return "feasible_balanced"
    if rc == "robust":
        return "feasible_robust"
    return "feasible"

def classify_candidate(
    candidate: Dict[str, Any],
    *,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
    dominant: bool = False,
) -> Dict[str, Any]:
    """Return a small classification dict for a candidate record."""
    feasible = bool(candidate.get("feasible", False))
    m = candidate.get("min_signed_margin", float("nan"))
    try:
        m = float(m)
    except Exception:
        m = float("nan")
    cons = candidate.get("constraints") or []
    ff = _first_failure(cons) if isinstance(cons, list) else None
    rc = robustness_class(m, thresholds=thresholds)
    fs = feasibility_state(feasible, m, thresholds=thresholds, dominant=dominant)
    return {
        "feasibility_state": fs,
        "robustness_class": rc,
        "first_failure": ff,
    }
