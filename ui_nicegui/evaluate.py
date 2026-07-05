"""Evaluator choke-point wrapper for the NiceGUI UI.

All point evaluations from ui_nicegui/ MUST go through ui_evaluate().
Matches PROPOSAL-008 / Streamlit _ui_evaluate() intent without Streamlit deps.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any, Dict, Optional

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui_nicegui.bootstrap import ensure_import_paths

ensure_import_paths()


@lru_cache(maxsize=1)
def _get_evaluator(**kwargs: Any):
    try:
        from src.evaluator.core import Evaluator  # type: ignore
    except Exception:
        from evaluator.core import Evaluator  # type: ignore
    return Evaluator(**kwargs)


def ui_evaluate(
    inp: Any,
    *,
    origin: str = "NiceGUI",
    Paux_for_Q_MW: Optional[float] = None,
    **evaluator_kwargs: Any,
) -> Dict[str, Any]:
    """Route NiceGUI point evaluation through the Evaluator choke point."""
    ev = _get_evaluator(**evaluator_kwargs)
    result = ev.evaluate(inp, Paux_for_Q_MW=Paux_for_Q_MW)
    out = getattr(result, "out", None)
    if isinstance(out, dict):
        return out
    if hasattr(result, "outputs") and isinstance(result.outputs, dict):
        return result.outputs
    raise TypeError(f"Unexpected Evaluator result type: {type(result)!r}")
