from __future__ import annotations

from typing import Callable, Dict, Optional
from models.inputs import PointInputs

# Registry for analytic partial derivatives:
# d(target)/d(var) at a given input state.
DerivativeFn = Callable[[PointInputs, dict], float]

_ANALYTIC: Dict[tuple[str, str], DerivativeFn] = {}

def register_derivative(target: str, var: str, fn: DerivativeFn) -> None:
    _ANALYTIC[(str(target), str(var))] = fn

def get_derivative(target: str, var: str) -> Optional[DerivativeFn]:
    return _ANALYTIC.get((str(target), str(var)))
