"""Auto-tag DSG edge kind when entering a deck (Streamlit parity)."""
from __future__ import annotations

from ui_nicegui.session import DesignSession

# Must match ui/dsg_panel.py and ui_nicegui/components/dsg_sidebar.py options.
_VALID_EDGE_KINDS = frozenset(
    {"derived", "systems_eval", "scan", "pareto", "trade", "extopt", "repair", "forge"}
)
_DECK_TO_EDGE_KIND: dict[str, str] = {
    "scan": "scan",
    "pareto": "pareto",
    "trade": "trade",
    "systems_eval": "systems_eval",
    "extopt": "extopt",
    "repair": "repair",
    "forge": "forge",
}

# NiceGUI deck display name → DSG edge kind token (normalized on apply).
DECK_NAME_EDGE_KIND: dict[str, str] = {
    "Point Designer": "derived",
    "Scan Lab": "scan",
    "Systems Mode": "systems_eval",
    "Opt Lab": "extopt",
    "Compare": "derived",
    "Pareto Lab": "pareto",
    "Trade Study Studio": "trade",
    "Reactor Design Forge": "forge",
    "Publication Benchmarks": "derived",
    "System Suite": "derived",
    "Control Room": "derived",
}


def deck_edge_kind_for(deck_name: str) -> str:
    return DECK_NAME_EDGE_KIND.get(str(deck_name), "derived")


def normalize_edge_kind(kind: str) -> str:
    k = str(kind)
    if k in _VALID_EDGE_KINDS:
        return k
    return _DECK_TO_EDGE_KIND.get(k, "derived")


def apply_deck_dsg_context(session: DesignSession, kind: str) -> None:
    if not getattr(session, "dsg_edge_kind_auto", True):
        return
    normalized = normalize_edge_kind(kind)
    # No-op when already tagged — avoids churn on same-kind remounts / force switches.
    if str(getattr(session, "dsg_context_edge_kind", "")) == normalized:
        return
    session.dsg_context_edge_kind = normalized
