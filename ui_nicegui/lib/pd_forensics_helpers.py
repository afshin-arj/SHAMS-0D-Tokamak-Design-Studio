"""Feasibility forensics wrapper for NiceGUI."""
from __future__ import annotations

from typing import Any, Dict, Optional


def run_local_forensics(base, *, design_intent: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic local sensitivity — delegates to src.analysis.forensics."""
    try:
        from src.analysis.forensics import local_sensitivity
    except ImportError:
        from analysis.forensics import local_sensitivity  # type: ignore
    return local_sensitivity(base, design_intent=design_intent)
