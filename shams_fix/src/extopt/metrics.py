from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple

@dataclass(frozen=True)
class FeasibilityMetrics:
    min_hard_margin: float
    sum_hard_violation: float
    n_hard_violations: int

def compute_feasibility_metrics(artifact: Dict[str, Any]) -> FeasibilityMetrics:
    """Compute optimizer-friendly scalars from a SHAMS run artifact.
    Convention:
      - margin > 0 means satisfied, margin < 0 violated (hard).
      - If constraints not present, returns conservative 'violated' values.
    """
    constraints = artifact.get("constraints", {})
    if not isinstance(constraints, dict) or not constraints:
        return FeasibilityMetrics(min_hard_margin=-1.0, sum_hard_violation=1.0, n_hard_violations=1)

    min_margin = float("inf")
    sum_violation = 0.0
    nvio = 0

    # We only use constraints that are explicitly hard. If missing, treat as diagnostic.
    for cname, c in constraints.items():
        if not isinstance(c, dict):
            continue
        kind = str(c.get("kind", c.get("tier", "diagnostic"))).lower()
        if kind not in ("hard", "hard_constraint"):
            continue
        margin = c.get("margin")
        try:
            m = float(margin)
        except Exception:
            continue
        if m < min_margin:
            min_margin = m
        if m < 0.0:
            nvio += 1
            sum_violation += (-m)

    if min_margin == float("inf"):
        # no hard constraints found
        min_margin = 0.0

    return FeasibilityMetrics(min_hard_margin=float(min_margin), sum_hard_violation=float(sum_violation), n_hard_violations=int(nvio))

def distance_to_feasible(artifact: Dict[str, Any]) -> float:
    """A scalar "distance" used by external optimizers. 0 if feasible under hard constraints."""
    m = compute_feasibility_metrics(artifact)
    return float(m.sum_hard_violation)
