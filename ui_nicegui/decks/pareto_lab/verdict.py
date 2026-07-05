"""Pareto Lab frontier dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_frontier_dashboard(summary: dict | None) -> None:
    ui.label("Frontier Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No Pareto study yet. Configure objectives and run a feasible-only study below.",
            kind="info",
        )
        return
    kpi_row([
        ("Feasible points", summary.get("n_feasible", "-")),
        ("Pareto points", summary.get("n_pareto", "-")),
        ("Top constraint", summary.get("top_constraint", "-")),
        ("Robust mix", summary.get("robust_mix", "-")),
        ("Confidence", summary.get("confidence", "-")),
    ])
