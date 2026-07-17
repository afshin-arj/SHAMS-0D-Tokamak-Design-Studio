"""empty_state — consistent no-data / unavailable placeholder."""
from __future__ import annotations

from nicegui import ui


def empty_state(message: str, *, kind: str = "info") -> None:
    if kind == "warning":
        kind = "warn"
    color = {
        "info": "bg-blue-grey-1",
        "warn": "bg-orange-1",
        "error": "bg-red-1",
    }.get(kind, "bg-blue-grey-1")
    with ui.card().classes(f"w-full p-4 {color}"):
        # Messages routinely carry **bold** deck/action names — render as markdown.
        ui.markdown(message).classes("text-body2")
