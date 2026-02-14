from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

# Keys commonly used for "design levers" across SHAMS presets.
DEFAULT_LEVERS: Tuple[str, ...] = (
    "R0_m","a_m","kappa","delta","B0_T",
    "Ip_MA","fG",
    "t_shield_m","t_blanket_m","t_vv_m",
    "Paux_MW","H98_target","Q_target",
)

# Map levers into coarse "decision budgets"
BUDGET_MAP: Dict[str, str] = {
    "R0_m": "capex",
    "a_m": "capex",
    "kappa": "performance",
    "delta": "performance",
    "B0_T": "capex",
    "Ip_MA": "performance",
    "fG": "performance",
    "t_shield_m": "reliability",
    "t_blanket_m": "reliability",
    "t_vv_m": "reliability",
    "Paux_MW": "opex",
}

def _scale(v0: float) -> float:
    try:
        v0f = float(v0)
    except Exception:
        return 1.0
    return max(abs(v0f), 1.0)

def trade_ledger(
    baseline_inputs: Dict[str, Any],
    solved_inputs: Dict[str, Any],
    *,
    levers: Tuple[str, ...] = DEFAULT_LEVERS,
) -> Dict[str, Any]:
    """Compute a simple, auditable trade ledger between a baseline and a solved design.

    Returns a dict with per-lever delta, scaled delta, and budget grouping. This is deliberately
    transparent (no hidden weights) and intended for decision-grade reporting.
    """
    items: List[Dict[str, Any]] = []
    budgets: Dict[str, float] = {}
    for k in levers:
        if k not in baseline_inputs or k not in solved_inputs:
            continue
        try:
            b = float(baseline_inputs[k])
            s = float(solved_inputs[k])
        except Exception:
            continue
        dv = s - b
        sd = dv / _scale(b)
        budget = BUDGET_MAP.get(k, "other")
        budgets[budget] = budgets.get(budget, 0.0) + abs(sd)
        items.append({
            "key": k,
            "baseline": b,
            "solved": s,
            "delta": dv,
            "delta_scaled": sd,
            "budget": budget,
        })
    # Sort by absolute scaled change descending
    items.sort(key=lambda x: abs(float(x.get("delta_scaled", 0.0))), reverse=True)
    return {
        "items": items,
        "budgets_abs_scaled": {k: float(v) for k,v in sorted(budgets.items(), key=lambda kv: -kv[1])},
    }
