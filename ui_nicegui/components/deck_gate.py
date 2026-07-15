"""Shared PD-gate empty state with Open Point Designer CTA."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.navigation import switch_deck


def pd_prerequisite_gate(message: str, *, kind: str = "info") -> None:
    """Show empty state + jump to Point Designer (common PD-gate pattern)."""
    empty_state(message, kind=kind)
    ui.button(
        "Open Point Designer",
        icon="design_services",
        on_click=lambda: switch_deck("Point Designer"),
    ).props("outline color=primary").classes("q-mt-sm")
