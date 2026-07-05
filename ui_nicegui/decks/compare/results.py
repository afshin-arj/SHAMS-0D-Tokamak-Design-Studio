"""Compare results tables and export (legacy — use metrics/export_panel)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.compare_helpers import (
    comparison_markdown,
    constraint_rows,
    metric_diff_rows,
    normalize_compare_artifact,
)


def render_comparison_results(art_a: dict, art_b: dict) -> None:
    ui.label("Key metrics").classes("text-subtitle2 q-mt-sm")
    rows = metric_diff_rows(art_a, art_b)
    if rows:
        ui.table(
            columns=[
                {"name": "metric", "label": "Metric", "field": "metric", "align": "left"},
                {"name": "A", "label": "A", "field": "A"},
                {"name": "B", "label": "B", "field": "B"},
                {"name": "B-A", "label": "B−A", "field": "B-A"},
            ],
            rows=rows,
            row_key="metric",
        ).classes("w-full")
    else:
        ui.label("No comparable metrics found in both artifacts.").classes("text-orange")

    ui.label("Constraints (worst margins first)").classes("text-subtitle2 q-mt-md")
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("Artifact A").classes("text-caption")
            _constraint_table(constraint_rows(art_a))
        with ui.column().classes("flex-1"):
            ui.label("Artifact B").classes("text-caption")
            _constraint_table(constraint_rows(art_b))

    md = comparison_markdown(art_a, art_b).encode("utf-8")
    ui.button(
        "Download comparison (markdown)",
        icon="download",
        on_click=lambda: ui.download(md, "artifact_comparison.md"),
    ).props("outline q-mt-sm")


def _constraint_table(rows: list[dict]) -> None:
    if not rows:
        ui.label("(no constraints)").classes("text-caption text-grey")
        return
    ui.table(
        columns=[
            {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
            {"name": "residual", "label": "Residual", "field": "residual"},
            {"name": "passed", "label": "Pass", "field": "passed"},
        ],
        rows=[{"name": r.get("name"), "residual": r.get("residual"), "passed": r.get("passed")} for r in rows],
        row_key="name",
    ).classes("w-full")
