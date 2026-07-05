"""Compare deck — constraint margins and feasibility shifts."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import constraint_margin_diff_rows, constraint_rows


def render_constraints_panel(art_a: dict, art_b: dict) -> None:
    diff_rows = constraint_margin_diff_rows(art_a, art_b)
    new_fail = [r for r in diff_rows if r.get("new_failure")]
    if new_fail:
        ui.label("New failures in B (passed in A)").classes("text-subtitle2 text-negative")
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "margin_A", "label": "Margin A", "field": "margin_A"},
                {"name": "margin_B", "label": "Margin B", "field": "margin_B"},
            ],
            rows=new_fail,
            row_key="name",
        ).classes("w-full q-mb-md")
    else:
        ui.label("No new constraint failures in B relative to A.").classes("text-caption text-positive q-mb-sm")

    ui.label("Margin regressions (largest Δ first)").classes("text-subtitle2")
    regressed = [r for r in diff_rows if r.get("margin_delta") is not None][:25]
    if regressed:
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "failed_A", "label": "Fail A", "field": "failed_A"},
                {"name": "failed_B", "label": "Fail B", "field": "failed_B"},
                {"name": "margin_A", "label": "Margin A", "field": "margin_A"},
                {"name": "margin_B", "label": "Margin B", "field": "margin_B"},
                {"name": "margin_delta", "label": "Δ margin", "field": "margin_delta"},
            ],
            rows=regressed,
            row_key="name",
        ).classes("w-full q-mb-md")
    else:
        empty_state("No margin deltas to report.", kind="info")

    ui.label("Worst margins per run (top 20)").classes("text-subtitle2 q-mt-sm")
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("Artifact A").classes("text-caption")
            _constraint_table(constraint_rows(art_a))
        with ui.column().classes("flex-1"):
            ui.label("Artifact B").classes("text-caption")
            _constraint_table(constraint_rows(art_b))


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
        rows=[
            {"name": r.get("name"), "residual": r.get("residual"), "passed": r.get("passed")}
            for r in rows
        ],
        row_key="name",
    ).classes("w-full")
