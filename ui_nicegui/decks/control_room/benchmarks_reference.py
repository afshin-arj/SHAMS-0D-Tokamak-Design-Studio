"""Control Room — reference tokamak benchmark table."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.control_room_helpers import BENCHMARK_REFERENCE_ROWS
from ui_nicegui.lib.navigation import switch_deck


def render_benchmark_reference(session: DesignSession) -> None:
    ui.label("Benchmark reference").classes("text-subtitle1")
    ui.label(
        "Quick lookup of major superconducting tokamaks used as comparison anchors. "
        "For rigorous comparison use **Publication Benchmarks** or cite primary parameter sheets."
    ).classes("text-caption text-grey q-mb-sm")

    ui.button(
        "Open Publication Benchmarks",
        on_click=lambda: switch_deck("Publication Benchmarks"),
    ).props("flat outline")

    if not BENCHMARK_REFERENCE_ROWS:
        ui.label("Reference table unavailable.").classes("text-grey")
        return

    cols = list(BENCHMARK_REFERENCE_ROWS[0].keys())
    ui.table(
        columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
        rows=BENCHMARK_REFERENCE_ROWS,
        row_key="Tokamak",
    ).classes("w-full")
    ui.label(
        "Values are typical/design-point screening numbers from public summaries — replace with cited values for publication."
    ).classes("text-caption text-grey q-mt-sm")
