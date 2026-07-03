"""Shared UI presentation components for SHAMS decks (UI redesign).

Pure presentation helpers. No physics, constraint, solver, evaluator, state,
or routing logic. Components here must never mutate session state beyond what
Streamlit widgets themselves do.
"""
from .kpi_row import kpi_row
from .empty_state import empty_state

__all__ = ["kpi_row", "empty_state"]
