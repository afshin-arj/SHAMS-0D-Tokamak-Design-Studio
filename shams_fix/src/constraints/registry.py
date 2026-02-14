from __future__ import annotations

"""
Constraint registry scaffold (PROCESS-inspired, SHAMS-independent)

This module provides a structured way to define, register, and pack constraints
for solvers and UI diagnostics.

It is designed to be *compatible* with SHAMS' existing constraint list
(`constraints.system.Constraint`) by offering conversion helpers. No behavior
changes are required to adopt it incrementally.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Any

from .constraints import Constraint


class ConstraintKind(str, Enum):
    """Constraint mathematical form."""

    EQ = "eq"      # equality: value == target
    INEQ = "ineq"  # inequality: lo <= value <= hi (or one-sided)


class ConstraintTier(str, Enum):
    """Constraint enforcement tier.

    - HARD: must be satisfied for feasibility
    - SOFT: treated as a penalty / preference (still reported with margins)
    """

    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class ConstraintSpec:
    """Metadata + evaluation hook for a single constraint.

    This is a PROCESS-inspired bookkeeping layer. It should remain stable over time
    so artifacts and studies can rely on consistent naming/semantics.
    """
    name: str
    kind: ConstraintKind = ConstraintKind.INEQ
    tier: ConstraintTier = ConstraintTier.HARD
    # Human-facing metadata
    units: str = "-"
    description: str = ""
    group: str = "general"  # e.g. plasma/magnets/pf/neutronics/economics/profiles
    sign_convention: str = "margin_pos_is_good"  # convention for residual interpretation

    # Activation / applicability
    active_in: List[str] = field(default_factory=list)  # empty => always active

    # Scaling / weighting
    scale: float = 1.0  # normalization scale for residuals (dimensionless)
    scaling_rule: str = "fractional_margin"  # documentation only
    weight: float = 1.0  # soft penalty weight (only used when tier=SOFT)
    evaluator: Optional[Callable[[Dict[str, float]], Constraint]] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstraintRegistry:
    """Collection of ConstraintSpec with packing/unpacking helpers."""
    specs: List[ConstraintSpec] = field(default_factory=list)

    def add(self, spec: ConstraintSpec) -> None:
        self.specs.append(spec)

    def names(self) -> List[str]:
        return [s.name for s in self.specs]

    @staticmethod
    def from_constraint_list(constraints: Sequence[Constraint]) -> "ConstraintRegistry":
        """Create a registry view from an existing SHAMS Constraint list."""
        reg = ConstraintRegistry()
        for c in constraints:
            # SHAMS constraints are typically inequalities. Treat any constraint
            # with sense '==' as EQ (rare; mostly future-facing).
            kind = ConstraintKind.EQ if getattr(c, "sense", "<=") == "==" else ConstraintKind.INEQ
            sev = str(getattr(c, "severity", "hard") or "hard").lower().strip()
            tier = ConstraintTier.SOFT if sev == "soft" else ConstraintTier.HARD
            reg.add(ConstraintSpec(
                name=c.name,
                kind=kind,
                tier=tier,
                units=getattr(c, "units", "-") or "-",
                description=getattr(c, "note", "") or "",
                group=str(getattr(c, "group", "general") or "general"),
                scale=1.0,
                weight=1.0,
                evaluator=None,
                meta={"legacy_units": getattr(c, "units", None)},
            ))
        return reg

    def active_specs(self, *, context: str | None = None) -> List[ConstraintSpec]:
        """Return specs active in the given context.

        If context is None, returns all specs.
        If spec.active_in is empty, it's treated as always active.
        """
        if context is None:
            return list(self.specs)
        out: List[ConstraintSpec] = []
        for s in self.specs:
            if not s.active_in or context in s.active_in:
                out.append(s)
        return out

    def classify(self, constraints: Sequence[Constraint]) -> Dict[str, List[Constraint]]:
        """Classify constraints into hard/soft and eq/ineq buckets.

        Returns a dict with keys:
          hard_eq, hard_ineq, soft_eq, soft_ineq
        """

        spec_by_name = {s.name: s for s in self.specs}
        buckets = {"hard_eq": [], "hard_ineq": [], "soft_eq": [], "soft_ineq": []}
        for c in constraints:
            spec = spec_by_name.get(c.name)
            tier = spec.tier if spec else (ConstraintTier.SOFT if str(getattr(c, "severity", "hard")).lower() == "soft" else ConstraintTier.HARD)
            kind = spec.kind if spec else (ConstraintKind.EQ if getattr(c, "sense", "<=") == "==" else ConstraintKind.INEQ)
            key = ("soft_" if tier == ConstraintTier.SOFT else "hard_") + ("eq" if kind == ConstraintKind.EQ else "ineq")
            buckets[key].append(c)
        return buckets

    def pack_for_solver(self, constraints: Sequence[Constraint]) -> Dict[str, Dict[str, float]]:
        """Pack constraints into solver-friendly residual dicts.

        - hard constraints are reported as residuals (negative margin = violation)
        - soft constraints are reported as weighted penalties (hinge loss)
        """

        spec_by_name = {s.name: s for s in self.specs}
        buckets = self.classify(constraints)

        def res(c: Constraint) -> float:
            # canonical residual: margin (dimensionless). negative => violated.
            try:
                r = float(c.margin)
            except Exception:
                r = 0.0
            spec = spec_by_name.get(c.name)
            sc = float(spec.scale) if spec and spec.scale else 1.0
            return r / sc if sc != 0 else r

        def penalty(c: Constraint) -> float:
            # hinge: only penalize violations
            m = res(c)
            spec = spec_by_name.get(c.name)
            w = float(spec.weight) if spec else 1.0
            return w * max(0.0, -m)

        packed = {
            "hard": {c.name: res(c) for c in buckets["hard_eq"] + buckets["hard_ineq"]},
            "soft": {c.name: penalty(c) for c in buckets["soft_eq"] + buckets["soft_ineq"]},
        }
        return packed

    def partition(self, constraints: Sequence[Constraint]) -> Tuple[List[Constraint], List[Constraint]]:
        """Partition a constraint list into (eq, ineq) using registry kinds (by name)."""
        kind_by_name = {s.name: s.kind for s in self.specs}
        eq, ineq = [], []
        for c in constraints:
            if kind_by_name.get(c.name, ConstraintKind.INEQ) == ConstraintKind.EQ:
                eq.append(c)
            else:
                ineq.append(c)
        return eq, ineq

    def pack_residuals(self, constraints: Sequence[Constraint]) -> Tuple[List[float], List[str]]:
        """Pack residuals into a solver-friendly vector, returning (residuals, names)."""
        res: List[float] = []
        names: List[str] = []
        scale_by_name = {s.name: (s.scale if s.scale else 1.0) for s in self.specs}
        for c in constraints:
            # Default residual uses signed fractional margin (negative = violated)
            try:
                r = float(c.margin)
            except Exception:
                r = 0.0
            sc = float(scale_by_name.get(c.name, 1.0))
            res.append(r / sc if sc != 0 else r)
            names.append(c.name)
        return res, names

    def pack_by_kind(self, constraints: Sequence[Constraint]) -> Dict[str, object]:
        """Return solver-friendly arrays for eq/ineq and hard/soft.

        Output keys:
          - hard_eq, hard_ineq: list[float] residuals (negative = violation)
          - soft_eq, soft_ineq: list[float] hinge penalties (>=0)
          - names: dict of parallel name lists
        """
        b = self.classify(constraints)
        spec_by_name = {s.name: s for s in self.specs}

        def r(c: Constraint) -> float:
            try:
                m = float(c.margin)
            except Exception:
                m = 0.0
            sc = float(spec_by_name.get(c.name, ConstraintSpec(c.name)).scale or 1.0)
            return m / sc if sc != 0 else m

        def p(c: Constraint) -> float:
            m = r(c)
            spec = spec_by_name.get(c.name)
            w = float(spec.weight) if spec else 1.0
            return w * max(0.0, -m)

        out = {
            "hard_eq": [r(c) for c in b["hard_eq"]],
            "hard_ineq": [r(c) for c in b["hard_ineq"]],
            "soft_eq": [p(c) for c in b["soft_eq"]],
            "soft_ineq": [p(c) for c in b["soft_ineq"]],
            "names": {
                "hard_eq": [c.name for c in b["hard_eq"]],
                "hard_ineq": [c.name for c in b["hard_ineq"]],
                "soft_eq": [c.name for c in b["soft_eq"]],
                "soft_ineq": [c.name for c in b["soft_ineq"]],
            },
        }
        return out
