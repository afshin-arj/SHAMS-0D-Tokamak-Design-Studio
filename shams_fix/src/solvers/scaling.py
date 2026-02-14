from __future__ import annotations

"""Scaling utilities for solver robustness.

PROCESS-style workflows get much of their robustness from consistent
normalization of both:

1) iteration variables (x)
2) residuals (r)

SHAMS keeps physics proxies transparent; scaling here is purely numerical.
The goal is to make solves comparable across machines/presets and improve
conditioning in Newton/least-squares updates.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class VariableScaling:
    """Per-variable scaling factors."""

    scale_by_name: Dict[str, float]

    def scale(self, name: str, value: float) -> float:
        s = float(self.scale_by_name.get(name, 1.0))
        return value / s if s != 0 else value

    def unscale(self, name: str, value_scaled: float) -> float:
        s = float(self.scale_by_name.get(name, 1.0))
        return value_scaled * s


@dataclass(frozen=True)
class ResidualScaling:
    """Per-residual scaling factors."""

    scale_by_name: Dict[str, float]

    def scale(self, name: str, residual: float) -> float:
        s = float(self.scale_by_name.get(name, 1.0))
        return residual / s if s != 0 else residual


def default_variable_scaling(x0: Dict[str, float]) -> VariableScaling:
    """Reasonable defaults from the current iterate.

    Uses max(|x0|, 1) to avoid divide-by-zero and keep dimensionless stability.
    """

    return VariableScaling({k: max(abs(float(v)), 1.0) for k, v in x0.items()})


def default_residual_scaling(targets: Dict[str, float]) -> ResidualScaling:
    """Scale residuals by target magnitude (or 1 if target ~0)."""

    return ResidualScaling({k: max(abs(float(v)), 1.0) for k, v in targets.items()})


def scale_bounds(bounds: List[Tuple[float, float]], scales: List[float]) -> List[Tuple[float, float]]:
    """Scale bounds for each variable."""

    out: List[Tuple[float, float]] = []
    for (lo, hi), s in zip(bounds, scales):
        s = float(s)
        if s == 0:
            out.append((lo, hi))
        else:
            out.append((lo / s, hi / s))
    return out
