"""Lazy-mount Quasar expansion bodies — avoid building heavy widgets until opened.

Deck switches remount the active deck. Eager Configure panels (dozens of
``ui.number`` / ``ui.select``) dominate switch latency. Nested expansion content
is identical whether collapsed or open in Quasar, so we defer body construction
until the user opens the panel.
"""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui


def lazy_expansion(
    title: str,
    *,
    icon: Optional[str] = None,
    help_text: Optional[str] = None,
    classes: str = "w-full",
    body: Callable[[], None],
) -> ui.expansion:
    """Create an expansion whose ``body`` runs once on first open."""
    state: dict = {"mounted": False, "slot": None}

    def _on_change(e) -> None:
        if state["mounted"] or not bool(getattr(e, "value", False)):
            return
        slot = state["slot"]
        if slot is None:
            return
        state["mounted"] = True
        with slot:
            body()

    exp = ui.expansion(title, icon=icon, on_value_change=_on_change).classes(classes)
    with exp:
        if help_text:
            ui.label(help_text).classes("text-caption q-mb-sm")
        state["slot"] = ui.column().classes("w-full")
        if exp.value:
            _on_change(type("_Evt", (), {"value": True})())
    return exp
