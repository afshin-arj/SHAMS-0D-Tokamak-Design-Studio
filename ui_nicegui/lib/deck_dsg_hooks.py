"""Auto-tag DSG edge kind when entering a deck (Streamlit parity)."""
from __future__ import annotations

from ui_nicegui.session import DesignSession

# Must match ui/dsg_panel.py and ui_nicegui/components/dsg_sidebar.py options.
_VALID_EDGE_KINDS = frozenset(
    {"derived", "systems_eval", "scan", "pareto", "trade", "extopt", "repair"}
)
_DECK_TO_EDGE_KIND: dict[str, str] = {
    "scan": "scan",
    "pareto": "pareto",
    "trade": "trade",
    "systems_eval": "systems_eval",
    "extopt": "extopt",
    "repair": "repair",
}


def normalize_edge_kind(kind: str) -> str:
    k = str(kind)
    if k in _VALID_EDGE_KINDS:
        return k
    return _DECK_TO_EDGE_KIND.get(k, "derived")


def apply_deck_dsg_context(session: DesignSession, kind: str) -> None:
    if getattr(session, "dsg_edge_kind_auto", True):
        session.dsg_context_edge_kind = normalize_edge_kind(kind)
