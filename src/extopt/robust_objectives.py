"""Robust objective contract schema (v296.0).

Defines a small canonical schema for robust optimization under:
- worst-phase
- worst-corner (uncertainty contracts)

This module is used to score candidates externally while keeping SHAMS truth
frozen. SHAMS remains the verifier.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


@dataclass(frozen=True)
class RobustObjectiveSpec:
    name: str
    direction: str = "max"  # max|min
    nominal_key: str = "objective_nominal"
    worst_phase_key: str = "objective_worst_phase"
    worst_corner_key: str = "objective_worst_corner"
    fragility_key: str = "fragility"


@dataclass(frozen=True)
class RobustObjectiveScore:
    nominal: float
    worst_phase: float
    worst_corner: float
    degradation_phase: float
    degradation_corner: float
    fragility: float


def score_from_evidence(evidence: Dict[str, Any], spec: RobustObjectiveSpec) -> RobustObjectiveScore:
    def _f(k: str, default: float = 0.0) -> float:
        v = evidence.get(k, default)
        try:
            return float(v)
        except Exception:
            return float(default)

    nom = _f(spec.nominal_key)
    wp = _f(spec.worst_phase_key, nom)
    wc = _f(spec.worst_corner_key, wp)
    frag = _f(spec.fragility_key, 0.0)

    # Degradation defined in the "loss" direction regardless of max/min.
    if spec.direction == "min":
        dph = nom - wp
        dco = nom - wc
    else:
        dph = nom - wp
        dco = nom - wc

    return RobustObjectiveScore(
        nominal=nom,
        worst_phase=wp,
        worst_corner=wc,
        degradation_phase=dph,
        degradation_corner=dco,
        fragility=frag,
    )
