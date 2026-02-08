from __future__ import annotations

from typing import Callable, Dict, Optional
try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore

# Registry for analytic partial derivatives:
# d(target)/d(var) at a given input state.
DerivativeFn = Callable[[PointInputs, dict], float]

_ANALYTIC: Dict[tuple[str, str], DerivativeFn] = {}

def register_derivative(target: str, var: str, fn: DerivativeFn) -> None:
    _ANALYTIC[(str(target), str(var))] = fn

def get_derivative(target: str, var: str) -> Optional[DerivativeFn]:
    return _ANALYTIC.get((str(target), str(var)))
