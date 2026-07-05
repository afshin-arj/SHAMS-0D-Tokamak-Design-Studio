"""Mode scope cards — what a deck does / does not do."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.mode_scope_data import MODE_SCOPE


def render_mode_scope(mode_key: str, *, default_open: bool = False) -> None:
    scope = MODE_SCOPE.get(str(mode_key))
    if not scope:
        return
    title = mode_key.replace("_", " ").title()
    with ui.expansion(f"Mode contract — {title}", icon="gavel", value=default_open).classes("w-full"):
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                ui.label("Does").classes("text-subtitle2 text-positive")
                for line in scope.get("does") or []:
                    ui.label(f"• {line}").classes("text-caption")
            with ui.column().classes("flex-1"):
                ui.label("Does not").classes("text-subtitle2 text-negative")
                for line in scope.get("does_not") or []:
                    ui.label(f"• {line}").classes("text-caption")
