"""Compare deck — performance KPIs and output deltas."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import kpi_diff_rows, metric_diff_rows, numeric_output_diff_rows
from ui_nicegui.lib.compare_labels import METRIC_DISPLAY
from ui_nicegui.session import DesignSession


def render_metrics_panel(session: DesignSession, art_a: dict, art_b: dict) -> None:
    ui.label("Key performance metrics").classes("text-subtitle2")
    rows = metric_diff_rows(art_a, art_b)
    if rows:
        display_rows = []
        for r in rows:
            key = str(r.get("metric", ""))
            display_rows.append(
                {
                    **r,
                    "label": METRIC_DISPLAY.get(key, key),
                }
            )
        ui.table(
            columns=[
                {"name": "label", "label": "Metric", "field": "label", "align": "left"},
                {"name": "A", "label": "A (baseline)", "field": "A"},
                {"name": "B", "label": "B (variant)", "field": "B"},
                {"name": "B-A", "label": "Δ B−A", "field": "B-A"},
            ],
            rows=display_rows,
            row_key="metric",
        ).classes("w-full")
    else:
        empty_state("No comparable key metrics in both artifacts.", kind="warn")

    kpi_rows = kpi_diff_rows(art_a, art_b)
    if kpi_rows:
        ui.label("Artifact KPI block").classes("text-subtitle2 q-mt-md")
        ui.table(
            columns=[
                {"name": "kpi", "label": "KPI", "field": "kpi", "align": "left"},
                {"name": "A", "label": "A", "field": "A"},
                {"name": "B", "label": "B", "field": "B"},
                {"name": "B-A", "label": "Δ", "field": "B-A"},
            ],
            rows=kpi_rows,
            row_key="kpi",
        ).classes("w-full")

    ui.separator().classes("q-my-sm")
    ui.switch(
        "Show all numeric output deltas (sorted by |Δ|)",
        value=session.cmp_show_all_outputs,
        on_change=lambda e: setattr(session, "cmp_show_all_outputs", bool(e.value)),
    )
    if session.cmp_show_all_outputs:
        all_rows = numeric_output_diff_rows(art_a, art_b)
        if all_rows:
            ui.table(
                columns=[
                    {"name": "metric", "label": "Output", "field": "metric", "align": "left"},
                    {"name": "A", "label": "A", "field": "A"},
                    {"name": "B", "label": "B", "field": "B"},
                    {"name": "B-A", "label": "Δ", "field": "B-A"},
                    {"name": "frac", "label": "Δ/A", "field": "frac"},
                ],
                rows=all_rows,
                row_key="metric",
            ).classes("w-full")
        else:
            ui.label("No numeric output differences detected.").classes("text-caption text-grey")
