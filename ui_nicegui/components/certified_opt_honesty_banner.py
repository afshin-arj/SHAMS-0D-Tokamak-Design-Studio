"""NiceGUI honesty banner for certified-search decks (Phase 1.3)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.certified_opt_honesty import (
    ATLAS_REJECT_NOTE,
    honesty_banner_for,
)


def render_certified_opt_honesty_banner(deck_key: str) -> None:
    """Render the shared Proposed — SHAMS-certified honesty strip."""
    ui.label(honesty_banner_for(deck_key)).classes("text-caption text-orange q-mb-sm")


def render_atlas_reject_note() -> None:
    """Caption under reject / infeasible result panels."""
    ui.label(ATLAS_REJECT_NOTE).classes("text-caption text-grey q-mb-xs")
