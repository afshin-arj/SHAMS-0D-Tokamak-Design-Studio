"""Evaluator choke-point wrapper for the NiceGUI UI.

All point evaluations from ui_nicegui/ MUST go through ui_evaluate() /
ui_evaluator(). Matches PROPOSAL-008 / Streamlit _ui_evaluate() intent
without Streamlit deps.

Do not construct ``Evaluator()`` elsewhere under ``ui_nicegui/`` — use
``ui_evaluator(origin=...)`` when a tool needs an evaluator-like object.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui_nicegui.bootstrap import ensure_import_paths

ensure_import_paths()

# Process-local Evaluator instances keyed by construction kwargs.
# Replaces fragile lru_cache(maxsize=1) which discarded origin labels.
_EVALUATOR_POOL: dict[tuple, Any] = {}


def _evaluator_pool_key(**kwargs: Any) -> tuple:
    items = []
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if isinstance(v, (str, int, float, bool)) or v is None:
            items.append((k, v))
        else:
            items.append((k, repr(v)))
    return tuple(items)


def _get_evaluator(**kwargs: Any):
    key = _evaluator_pool_key(**kwargs)
    ev = _EVALUATOR_POOL.get(key)
    if ev is not None:
        return ev
    try:
        from src.evaluator.core import Evaluator  # type: ignore
    except Exception:
        from evaluator.core import Evaluator  # type: ignore
    ev = Evaluator(**kwargs)
    _EVALUATOR_POOL[key] = ev
    return ev


@dataclass
class EvalResultShim:
    """Minimal EvalResult duck-type for tools that read ``.out`` / ``.ok``."""

    inp: Any
    out: Dict[str, Any]
    elapsed_s: float = 0.0
    ok: bool = True
    message: str = ""


class UiEvaluatorAdapter:
    """Evaluator-compatible facade whose ``.evaluate()`` always calls ``ui_evaluate``.

    Use this wherever Scan/Trade/Systems helpers previously constructed a bare
    ``Evaluator()``. Provenance ``origin`` is forwarded as the Evaluator label.
    """

    def __init__(
        self,
        *,
        origin: str = "NiceGUI",
        cache_enabled: bool = True,
        cache_max: int = 4096,
    ) -> None:
        self.origin = str(origin or "NiceGUI")
        self.label = self.origin
        self._cache_enabled = bool(cache_enabled)
        self._cache_max = int(cache_max)

    def evaluate(self, inp: Any, Paux_for_Q_MW: Optional[float] = None) -> EvalResultShim:
        t0 = time.perf_counter()
        out = ui_evaluate(
            inp,
            origin=self.origin,
            Paux_for_Q_MW=Paux_for_Q_MW,
            label=self.origin,
            cache_enabled=self._cache_enabled,
            cache_max=self._cache_max,
        )
        return EvalResultShim(
            inp=inp,
            out=out if isinstance(out, dict) else {},
            elapsed_s=float(time.perf_counter() - t0),
            ok=isinstance(out, dict),
            message="" if isinstance(out, dict) else "non-dict outputs",
        )

    def get(self, inp: Any, key: str, default: float = float("nan")) -> float:
        res = self.evaluate(inp)
        try:
            return float((res.out or {}).get(key, default))
        except (TypeError, ValueError):
            return default

    def cache_stats(self) -> Dict[str, Any]:
        ev = _get_evaluator(
            label=self.origin,
            cache_enabled=self._cache_enabled,
            cache_max=self._cache_max,
        )
        return ev.cache_stats()

    def reset_cache_stats(self) -> None:
        ev = _get_evaluator(
            label=self.origin,
            cache_enabled=self._cache_enabled,
            cache_max=self._cache_max,
        )
        ev.reset_cache_stats()

    @staticmethod
    def residuals(
        out: Dict[str, float],
        targets: Dict[str, float],
        senses: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        try:
            from src.evaluator.core import Evaluator  # type: ignore
        except Exception:
            from evaluator.core import Evaluator  # type: ignore
        return Evaluator.residuals(out, targets, senses)

    @staticmethod
    def residual_norm(residuals: Dict[str, float]) -> float:
        try:
            from src.evaluator.core import Evaluator  # type: ignore
        except Exception:
            from evaluator.core import Evaluator  # type: ignore
        return Evaluator.residual_norm(residuals)


def ui_evaluator(
    *,
    origin: str = "NiceGUI",
    cache_enabled: bool = True,
    cache_max: int = 4096,
) -> UiEvaluatorAdapter:
    """Factory for Evaluator-compatible objects that route through ui_evaluate."""
    return UiEvaluatorAdapter(origin=origin, cache_enabled=cache_enabled, cache_max=cache_max)


def ui_evaluate(
    inp: Any,
    *,
    origin: str = "NiceGUI",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluator_kwargs: Any,
) -> Dict[str, Any]:
    """Route NiceGUI point evaluation through the Evaluator choke point."""
    evaluator_kwargs.setdefault("label", str(origin or "NiceGUI"))
    ev = _get_evaluator(**evaluator_kwargs)
    result = ev.evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW)
    out = getattr(result, "out", None)
    if isinstance(out, dict):
        return out
    if hasattr(result, "outputs") and isinstance(result.outputs, dict):
        return result.outputs
    raise TypeError(f"Unexpected Evaluator result type: {type(result)!r}")
