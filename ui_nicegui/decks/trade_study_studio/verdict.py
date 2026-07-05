"""Trade Study verdict-first dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_study_dashboard(summary: dict | None) -> None:
    ui.label("Trade Study Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No trade study yet. Select a knob set and run a deterministic study below.",
            kind="info",
        )
        return
    objs = summary.get("objectives") or []
    obj_label = ", ".join(objs[:3]) + ("…" if len(objs) > 3 else "")
    kpi_row([
        ("Samples", summary.get("n_samples", "-")),
        ("Feasible", summary.get("n_feasible", "-")),
        ("Pareto", summary.get("n_pareto", "-")),
        ("Confidence", summary.get("confidence", "-")),
        ("Knob set", summary.get("knob_set", "-")),
    ])
    if obj_label:
        ui.label(f"Objectives: {obj_label} · seed={summary.get('seed', '-')}").classes(
            "text-caption text-grey q-mb-sm"
        )
