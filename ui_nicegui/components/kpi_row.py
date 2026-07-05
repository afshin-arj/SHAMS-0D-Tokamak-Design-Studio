"""kpi_row — compact horizontal KPI strip (NiceGUI).

Pure presentation. No physics, no evaluation, no session mutation.
"""
from __future__ import annotations

from typing import Sequence

from nicegui import ui


def kpi_row(items: Sequence[tuple[str, object] | tuple[str, object, str] | None]) -> None:
    cells = [it for it in items if it is not None]
    if not cells:
        return
    with ui.row().classes("w-full gap-2"):
        for it in cells:
            label = str(it[0])
            value = it[1] if len(it) > 1 else ""
            help_text = it[2] if len(it) > 2 else None
            with ui.card().classes("flex-1 p-3"):
                ui.label(label).classes("text-caption text-grey")
                ui.label(str(value)).classes("text-h6")
                if help_text:
                    ui.label(str(help_text)).classes("text-caption text-grey-6")
