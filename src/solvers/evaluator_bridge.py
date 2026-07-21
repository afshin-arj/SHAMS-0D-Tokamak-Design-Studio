"""Evaluator choke-point bridge for solvers and frontier kits (PROPOSAL-023).

NiceGUI sets an override via ``set_evaluate_point_override`` so Pareto / optimize
paths route through ``ui_evaluate`` without importing ``ui_nicegui`` into ``src/``.
CLI and tests keep the bare ``Evaluator`` fallback.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

# Optional override: (inp, *, origin, Paux_for_Q_MW, **kwargs) -> dict outputs
_EVALUATE_OVERRIDE: Optional[Callable[..., Dict[str, Any]]] = None
# Fallback Evaluator pool keyed by origin (avoids sticky first-label singleton).
_EVALUATOR_POOL: Dict[str, Any] = {}


def set_evaluate_point_override(fn: Optional[Callable[..., Dict[str, Any]]] = None) -> None:
    """Install or clear a process-local evaluate_point override (NiceGUI choke point)."""
    global _EVALUATE_OVERRIDE
    _EVALUATE_OVERRIDE = fn


def evaluate_point(
    inp: PointInputs,
    *,
    origin: str = "solver",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluator_kwargs: Any,
) -> Dict[str, Any]:
    if _EVALUATE_OVERRIDE is not None:
        out = _EVALUATE_OVERRIDE(
            inp,
            origin=str(origin),
            Paux_for_Q_MW=Paux_for_Q_MW,
            **evaluator_kwargs,
        )
        return dict(out) if isinstance(out, dict) else {}

    try:
        from evaluator.core import Evaluator  # type: ignore
    except ImportError:
        from src.evaluator.core import Evaluator  # type: ignore

    key = str(origin or "solver")
    ev = _EVALUATOR_POOL.get(key)
    if ev is None:
        ev = Evaluator(label=key, cache_enabled=True, **evaluator_kwargs)
        _EVALUATOR_POOL[key] = ev
    res = ev.evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW)
    out = getattr(res, "out", None)
    return dict(out) if isinstance(out, dict) else {}


def evaluate_point_with_constraints(
    inp: PointInputs,
    *,
    origin: str = "solver",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluate_kwargs: Any,
):
    from constraints.unified import build_all_constraints

    out = evaluate_point(inp, origin=origin, Paux_for_Q_MW=Paux_for_Q_MW)
    bundle = build_all_constraints(out, **evaluate_kwargs)
    return out, bundle
