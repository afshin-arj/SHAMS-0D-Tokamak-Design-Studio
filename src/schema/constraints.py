"""Constraint record (L0 schema).

The :class:`Constraint` dataclass used by the PointInputs -> physics ->
constraints data flow. Moved here from :mod:`constraints.system` in Tier-3
Batch B1 so the pure data record lives in the schema layer, independent of the
constraint-building logic. ``constraints.system`` re-imports it, so
``from constraints.system import Constraint`` keeps working unchanged.

Note: a *different*, richer ``Constraint`` type exists in
:mod:`constraints.constraints` (governance/cartography metadata). That type is
unrelated and is intentionally left where it is.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Constraint:
    name: str
    value: float
    lo: Optional[float] = None
    hi: Optional[float] = None
    units: str = "-"
    description: str = ""

    @property
    def ok(self) -> bool:
        if self.lo is not None and self.value < self.lo:
            return False
        if self.hi is not None and self.value > self.hi:
            return False
        return True

    def residual(self) -> float:
        """Normalized violation (0 if satisfied)."""
        if self.lo is not None and self.value < self.lo:
            denom = abs(self.lo) if abs(self.lo) > 1e-9 else 1.0
            return (self.lo - self.value) / denom
        if self.hi is not None and self.value > self.hi:
            denom = abs(self.hi) if abs(self.hi) > 1e-9 else 1.0
            return (self.value - self.hi) / denom
        return 0.0
