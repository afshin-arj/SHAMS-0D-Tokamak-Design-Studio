"""Evaluator choke-point bridge for solvers and frontier kits (PROPOSAL-023)."""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

_EVALUATOR = None


def evaluate_point(
    inp: PointInputs,
    *,
    origin: str = "solver",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluator_kwargs: Any,
) -> Dict[str, Any]:
    global _EVALUATOR
    try:
        from evaluator.core import Evaluator  # type: ignore
    except ImportError:
        from src.evaluator.core import Evaluator  # type: ignore

    if _EVALUATOR is None:
        _EVALUATOR = Evaluator(label=str(origin), cache_enabled=True, **evaluator_kwargs)
    res = _EVALUATOR.evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW)
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
