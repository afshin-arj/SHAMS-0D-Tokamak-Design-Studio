"""Auto-tag DSG edge kind when entering a deck (Streamlit parity)."""
from __future__ import annotations

from ui_nicegui.session import DesignSession


def apply_deck_dsg_context(session: DesignSession, kind: str) -> None:
    if getattr(session, "dsg_edge_kind_auto", True):
        session.dsg_context_edge_kind = str(kind)
