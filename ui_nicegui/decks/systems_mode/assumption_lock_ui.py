"""Assumption lock UI — capture settings hash and block solve on drift."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.systems_assumption_lock import (
    assumption_settings_hash,
    check_assumption_lock,
)
from ui_nicegui.session import DesignSession


def render_assumption_lock_bar(session: DesignSession) -> None:
    current = assumption_settings_hash(session)
    locked = str(session.systems_assumption_lock_hash or "")
    ok, msg = check_assumption_lock(session)

    with ui.row().classes("items-center gap-2 flex-wrap q-mb-sm"):
        ui.checkbox(
            "Assumption lock (block solve/precheck on drift)",
            value=bool(session.systems_assumption_lock_enabled),
            on_change=lambda e: setattr(session, "systems_assumption_lock_enabled", bool(e.value)),
        )
        ui.label(f"Hash: {current}").classes("text-caption text-grey")

    if session.systems_assumption_lock_enabled and locked:
        ui.label(f"Locked: {locked}").classes("text-caption")
        if not ok:
            ui.label(msg).classes("text-caption text-negative")

    def _capture() -> None:
        session.systems_assumption_lock_hash = current
        session.systems_assumption_lock_enabled = True
        ui.notify("Assumption lock captured", type="positive")

    def _clear() -> None:
        session.systems_assumption_lock_hash = ""
        ui.notify("Lock cleared", type="info")

    with ui.row().classes("gap-2 q-mb-sm"):
        ui.button("Capture lock", on_click=_capture).props("flat dense")
        ui.button("Clear lock", on_click=_clear).props("flat dense")


def assumption_lock_blocks(session: DesignSession) -> tuple[bool, str]:
    """Return (blocked, message) for precheck/solve handlers."""
    if not session.systems_assumption_lock_enabled:
        return False, ""
    ok, msg = check_assumption_lock(session)
    if ok:
        return False, ""
    return True, msg
