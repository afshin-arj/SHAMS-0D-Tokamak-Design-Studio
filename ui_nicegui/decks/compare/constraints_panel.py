"""Compare deck — constraint margins and feasibility shifts."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import (
    constraint_margin_diff_rows,
    constraint_rows,
    new_hard_failures_caption,
    normalize_compare_artifact,
)
from ui_nicegui.lib.verdict_core import verdict_summary


def render_constraints_panel(art_a: dict, art_b: dict) -> None:
    diff_rows = constraint_margin_diff_rows(art_a, art_b)
    new_fail = [r for r in diff_rows if r.get("new_failure")]
    na = normalize_compare_artifact(art_a)
    nb = normalize_compare_artifact(art_b)
    feas_a = bool(verdict_summary(na.get("outputs") or {}).get("feasible"))
    feas_b = bool(verdict_summary(nb.get("outputs") or {}).get("feasible"))
    caption, caption_cls = new_hard_failures_caption(
        feas_a=feas_a,
        feas_b=feas_b,
        n_new_fail=len(new_fail),
    )
    ui.label(caption).classes(caption_cls)
    if new_fail:
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "severity_B", "label": "Severity B", "field": "severity_B"},
                {"name": "margin_A", "label": "Margin A", "field": "margin_A"},
                {"name": "margin_B", "label": "Margin B", "field": "margin_B"},
            ],
            rows=new_fail,
            row_key="name",
        ).classes("w-full q-mb-md")

    ui.label("Margin regressions (largest Δ first)").classes("text-subtitle2")
    ui.label(
        "Fail columns are hard-severity only; soft/diagnostic appear under soft_failed_*."
    ).classes("text-caption text-grey q-mb-xs")
    regressed = [r for r in diff_rows if r.get("margin_delta") is not None][:25]
    if regressed:
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "severity_A", "label": "Sev A", "field": "severity_A"},
                {"name": "severity_B", "label": "Sev B", "field": "severity_B"},
                {"name": "failed_A", "label": "Hard fail A", "field": "failed_A"},
                {"name": "failed_B", "label": "Hard fail B", "field": "failed_B"},
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
