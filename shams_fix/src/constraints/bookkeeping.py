from __future__ import annotations

"""Constraint bookkeeping (PROCESS-inspired, SHAMS-friendly).

PROCESS maintains explicit bookkeeping of equality/inequality counts and
enforcement tiers. SHAMS expresses constraints as a list of `Constraint` with a
`severity` flag. This module provides a clear, consistent mapping:

- HARD constraints determine feasibility
- SOFT constraints contribute a penalty score (but do not determine feasibility)

All values are computed from the canonical margin convention:
  margin_frac < 0  -> violation
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constraints import Constraint
from .registry import ConstraintRegistry, ConstraintTier


@dataclass(frozen=True)
class ConstraintSummary:
    n_total: int
    n_hard: int
    n_soft: int
    n_hard_failed: int
    worst_hard_margin_frac: Optional[float]
    worst_hard: Optional[str]
    soft_penalty_sum: float
    feasible: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_total": int(self.n_total),
            "n_hard": int(self.n_hard),
            "n_soft": int(self.n_soft),
            "n_hard_failed": int(self.n_hard_failed),
            "worst_hard_margin_frac": float(self.worst_hard_margin_frac) if self.worst_hard_margin_frac is not None else None,
            "worst_hard": self.worst_hard,
            "soft_penalty_sum": float(self.soft_penalty_sum),
            "feasible": bool(self.feasible),
        }


def summarize_by_group(constraints: List[Constraint]) -> Dict[str, Any]:
    """Summarize constraints grouped by their `group` field.

    Returns a dict like:
      {group: {n_hard, n_soft, n_hard_failed, worst_hard_margin_frac, soft_penalty_sum}}
    """

    reg = ConstraintRegistry.from_constraint_list(constraints)
    spec_by_name = {s.name: s for s in reg.specs}

    groups: Dict[str, Dict[str, Any]] = {}
    for c in constraints:
        g = str(getattr(c, "group", "general") or "general")
        if g not in groups:
            groups[g] = {
                "n_hard": 0,
                "n_soft": 0,
                "n_hard_failed": 0,
                "worst_hard_margin_frac": None,
                "soft_penalty_sum": 0.0,
            }
        spec = spec_by_name.get(c.name)
        tier = spec.tier if spec else (ConstraintTier.SOFT if str(getattr(c, "severity", "hard")).lower() == "soft" else ConstraintTier.HARD)
        if tier == ConstraintTier.SOFT:
            groups[g]["n_soft"] += 1
            try:
                groups[g]["soft_penalty_sum"] += float(max(0.0, -float(c.margin)))
            except Exception:
                pass
        else:
            groups[g]["n_hard"] += 1
            if not bool(getattr(c, "passed", True)):
                groups[g]["n_hard_failed"] += 1
            try:
                mf = float(c.margin)
                cur = groups[g]["worst_hard_margin_frac"]
                if cur is None or mf < float(cur):
                    groups[g]["worst_hard_margin_frac"] = float(mf)
            except Exception:
                pass
    return groups


def summarize(constraints: List[Constraint], registry: Optional[ConstraintRegistry] = None) -> ConstraintSummary:
    """Summarize constraints with explicit tier bookkeeping.

    If registry is not provided, it is inferred from the constraint list.
    """

    reg = registry or ConstraintRegistry.from_constraint_list(constraints)
    buckets = reg.classify(constraints)
    hard = buckets["hard_eq"] + buckets["hard_ineq"]
    soft = buckets["soft_eq"] + buckets["soft_ineq"]

    n_hard_failed = sum(0 if c.passed else 1 for c in hard)
    worst = None
    worst_name = None
    for c in hard:
        try:
            mf = float(c.margin)
        except Exception:
            continue
        if worst is None or mf < worst:
            worst = mf
            worst_name = c.name

    packed = reg.pack_for_solver(constraints)
    soft_penalty_sum = float(sum(float(v) for v in (packed.get("soft") or {}).values()))

    return ConstraintSummary(
        n_total=len(constraints),
        n_hard=len(hard),
        n_soft=len(soft),
        n_hard_failed=n_hard_failed,
        worst_hard_margin_frac=worst,
        worst_hard=worst_name,
        soft_penalty_sum=soft_penalty_sum,
        feasible=(n_hard_failed == 0),
    )
