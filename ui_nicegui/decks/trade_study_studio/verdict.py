"""Trade Study verdict-first dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.trade_study_helpers import frontier_posture


def render_study_dashboard(summary: dict | None, *, design_intent: str = "") -> None:
    ui.label("Trade Study Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No trade study yet. Configure knobs and run a blocking-OK (intent-gate) study on **Setup & Run**.",
            kind="info",
        )
        return
    if design_intent:
        ui.badge(f"Intent-gate lens: {design_intent}", color="blue-grey").props("outline").classes(
            "q-mb-xs"
        )
    from ui_nicegui.components.verdict_banner import verdict_banner

    posture, tone = frontier_posture(summary)
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

    objs = summary.get("objectives") or []
    obj_label = ", ".join(objs[:3]) + ("…" if len(objs) > 3 else "")
    kpi_row([
        ("Samples", summary.get("n_samples", "-")),
        ("blocking-OK", summary.get("n_feasible", "-")),
        ("Pareto", summary.get("n_pareto", "-")),
        ("Sampling dens.", summary.get("confidence", "-")),
        ("Knob set", summary.get("knob_set", "-")),
    ])
    ui.label(
        "Sample density is not UQ confidence. "
        "blocking-OK = intent-gate / governance hard-pass on LHS samples — not L0 FEASIBLE."
    ).classes("text-caption text-grey q-mt-xs")
    if obj_label:
        ui.label(f"Objectives: {obj_label} · seed={summary.get('seed', '-')}").classes(
            "text-caption text-grey q-mb-sm"
        )
