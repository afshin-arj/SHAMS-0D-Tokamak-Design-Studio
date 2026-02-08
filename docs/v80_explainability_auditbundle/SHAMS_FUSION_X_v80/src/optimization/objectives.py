from __future__ import annotations

"""Objective registry.

PROCESS-style work typically defines objectives (min R0, min Bpeak, min COE, max Pnet, ...)
and uses them consistently across studies, Pareto exploration, and optimization.

SHAMS keeps this transparent: objectives are just named functions of the model output dict.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class ObjectiveSpec:
    name: str
    sense: str  # "min" or "max"
    fn: Callable[[Dict[str, float]], float]
    description: str = ""


_REGISTRY: Dict[str, ObjectiveSpec] = {}


def register_objective(spec: ObjectiveSpec) -> None:
    _REGISTRY[spec.name] = spec


def get_objective(name: str) -> Optional[ObjectiveSpec]:
    return _REGISTRY.get(name)


def list_objectives() -> Dict[str, ObjectiveSpec]:
    return dict(_REGISTRY)


def _safe(out: Dict[str, float], key: str, default: float) -> float:
    try:
        v = float(out.get(key, default))
    except Exception:
        v = default
    return v


def register_default_objectives() -> None:
    """Register a standard set of objectives used by UI and studies."""

    register_objective(ObjectiveSpec(
        name="min_R0",
        sense="min",
        fn=lambda out: _safe(out, "R0_m", 1e9),
        description="Minimize major radius",
    ))
    register_objective(ObjectiveSpec(
        name="min_Bpeak",
        sense="min",
        fn=lambda out: _safe(out, "B_peak_T", 1e9),
        description="Minimize peak TF field",
    ))
    register_objective(ObjectiveSpec(
        name="max_Pnet",
        sense="max",
        fn=lambda out: _safe(out, "P_e_net_MW", -1e9),
        description="Maximize net electric power",
    ))
    register_objective(ObjectiveSpec(
        name="min_COE",
        sense="min",
        fn=lambda out: _safe(out, "COE_proxy_USD_per_MWh", 1e9),
        description="Minimize cost of electricity proxy",
    ))
    register_objective(ObjectiveSpec(
        name="min_precirc",
        sense="min",
        fn=lambda out: _safe(out, "P_recirc_MW", 1e9),
        description="Minimize recirculating power",
    ))


# register defaults at import time (safe: pure functions)
register_default_objectives()
