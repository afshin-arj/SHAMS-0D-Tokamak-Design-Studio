"""Pareto Lab frontier dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.pareto_helpers import frontier_posture


def render_frontier_dashboard(summary: dict | None, *, intent_mode: str = "") -> None:
    ui.label("Frontier Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No Pareto study yet. Configure objectives and run a blocking-OK (intent-gate) study on **Setup & Run** "
            "(requires a **Point Designer** baseline).",
            kind="info",
        )
        ui.button(
            "Open Point Designer",
            icon="design_services",
            on_click=lambda: switch_deck("Point Designer"),
        ).props("outline color=primary").classes("q-mt-sm")
        return

    if intent_mode:
        ui.badge(f"Intent-gate lens: {intent_mode}", color="blue-grey").props("outline").classes(
            "q-mb-xs"
        )

    posture, tone = frontier_posture(summary)
    from ui_nicegui.components.verdict_banner import verdict_banner

    # Never paint sampling density as L0 green PASS / FEASIBLE.
    if tone == "negative":
        banner_posture = "FAIL"
    elif tone == "warning":
        banner_posture = "MIXED"
    else:
        banner_posture = "BLOCKING-OK SCREENING"
    verdict_banner(
        banner_posture,
        detail=posture,
        title_prefix="Frontier screening posture",
    )

    feas_frac = summary.get("feasible_fraction")
    feas_pct = f"{100.0 * float(feas_frac):.1f}%" if isinstance(feas_frac, (int, float)) else "-"
    conf = str(summary.get("confidence") or "-")
    conf_color = {
        "Sampling-dense": "info",
        "High": "info",
        "Sampling-moderate": "info",
        "Moderate": "info",
        "Sampling-sparse": "warning",
        "Low": "warning",
        "Sparse": "negative",
    }.get(conf, "grey")

    kpi_row([
        ("blocking-OK", summary.get("n_feasible", "-")),
        ("Pareto", summary.get("n_pareto", "-")),
        ("blocking-OK fraction", feas_pct),
        ("Top limiter", summary.get("top_constraint", "-")),
        ("Margin-robust mix", summary.get("robust_mix", "-")),
        ("Mirage mix", summary.get("mirage_mix", "-")),
    ])
    ui.badge(f"Sample density: {conf}", color=conf_color).props("outline").classes("q-mt-xs")
    ui.label(
        "Sample density is not UQ/resampling confidence. "
        "Margin-robust mix = Pareto points with min_constraint_margin ≥ threshold. "
        "Mirage mix = blocking-OK but credibility-fragile — screening only; not L0 FEASIBLE."
    ).classes("text-caption text-grey q-mt-xs")
