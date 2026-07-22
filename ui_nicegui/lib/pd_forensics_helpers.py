"""Feasibility forensics wrapper for NiceGUI."""
from __future__ import annotations

from typing import Any, Dict, Optional


def run_local_forensics(base, *, design_intent: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic local sensitivity — delegates to src.analysis.forensics via ui_evaluate."""
    try:
        from src.analysis.forensics import local_sensitivity
    except ImportError:
        from analysis.forensics import local_sensitivity  # type: ignore
    from ui_nicegui.evaluate import ui_evaluate

    def _eval(inp):
        return ui_evaluate(inp, origin="NiceGUI:Forensics")

    return local_sensitivity(base, design_intent=design_intent, evaluate_fn=_eval)
