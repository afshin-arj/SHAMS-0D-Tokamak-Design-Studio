"""Pareto Lab frontier dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pareto_helpers import frontier_posture


def render_frontier_dashboard(summary: dict | None) -> None:
    ui.label("Frontier Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No Pareto study yet. Configure objectives and run a feasible-only study below.",
            kind="info",
        )
        return

    posture, tone = frontier_posture(summary)
    tone_cls = {
        "positive": "text-positive",
        "warning": "text-orange",
        "negative": "text-negative",
        "info": "text-grey",
    }.get(tone, "text-grey")
    ui.label(posture).classes(f"text-body2 q-mb-sm {tone_cls}")

    feas_frac = summary.get("feasible_fraction")
    feas_pct = f"{100.0 * float(feas_frac):.1f}%" if isinstance(feas_frac, (int, float)) else "-"
    conf = str(summary.get("confidence") or "-")
    conf_color = {
        "High": "positive",
        "Moderate": "info",
        "Low": "warning",
        "Sparse": "negative",
    }.get(conf, "grey")

    kpi_row([
        ("Feasible", summary.get("n_feasible", "-")),
        ("Pareto", summary.get("n_pareto", "-")),
        ("Feasible fraction", feas_pct),
        ("Top limiter", summary.get("top_constraint", "-")),
        ("Margin-robust mix", summary.get("robust_mix", "-")),
        ("Mirage mix", summary.get("mirage_mix", "-")),
    ])
    ui.badge(f"Sampling confidence: {conf}", color=conf_color).props("outline").classes("q-mt-xs")
    ui.label(
        "Margin-robust mix = Pareto points with min_constraint_margin ≥ threshold (not UQ robustness). "
        "Mirage mix = feasible but credibility-fragile (v402) — screening only."
    ).classes("text-caption text-grey q-mt-xs")
