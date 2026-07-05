"""Placeholder deck until Phase 4 port."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.session import DesignSession


def render_stub_deck(session: DesignSession, deck_name: str) -> None:
    empty_state(
        f"{deck_name} is not yet ported to NiceGUI. "
        "Use Streamlit: run_ui.cmd (port 8501). "
        f"Track progress in /shams-nicegui-migration.",
        kind="info",
    )
    ui.separator()
    ui.label(f"Active deck: {deck_name}").classes("text-caption text-grey")
