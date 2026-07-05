"""verdict_banner — verdict-first posture strip."""
from __future__ import annotations

from nicegui import ui


def verdict_banner(posture: str, *, detail: str = "") -> None:
    p = str(posture or "UNKNOWN").upper()
    style = {
        "FEASIBLE": "bg-green-1 text-green-10",
        "INFEASIBLE": "bg-red-1 text-red-10",
        "NO-SOLUTION": "bg-orange-1 text-orange-10",
        "MIRAGE": "bg-purple-1 text-purple-10",
    }.get(p, "bg-grey-2")
    with ui.card().classes(f"w-full p-3 {style}"):
        ui.label(f"Verdict: {p}").classes("text-h6")
        if detail:
            ui.label(detail).classes("text-body2")
