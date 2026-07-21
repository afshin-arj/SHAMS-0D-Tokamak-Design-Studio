"""Trade Study verdict-first dashboard."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_study_dashboard(summary: dict | None, *, design_intent: str = "") -> None:
    ui.label("Trade Study Dashboard").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary:
        empty_state(
            "No trade study yet. Select a knob set and run a deterministic study below.",
            kind="info",
        )
        return
    if design_intent:
        ui.badge(f"Feasibility lens: {design_intent}", color="blue-grey").props("outline").classes(
            "q-mb-xs"
        )
    from ui_nicegui.components.verdict_banner import verdict_banner

    n_feas = int(summary.get("n_feasible") or 0)
    n_par = int(summary.get("n_pareto") or 0)
    if n_feas == 0:
        verdict_banner("FAIL", detail="No feasible samples — widen knob set or change intent lens.")
    elif n_par == 0:
        verdict_banner("MIXED", detail="Feasible samples exist but no Pareto set yet.")
    else:
        # Sampling confidence is not design certification (PHYS-KPI-001 / honesty).
        verdict_banner(
            "PASS+DIAG",
            detail=(
                f"{n_feas} feasible · {n_par} Pareto. "
                f"Sampling confidence={summary.get('confidence', '-')} — not a certified design PASS."
            ),
        )
    objs = summary.get("objectives") or []
    obj_label = ", ".join(objs[:3]) + ("…" if len(objs) > 3 else "")
    kpi_row([
        ("Samples", summary.get("n_samples", "-")),
        ("Feasible", summary.get("n_feasible", "-")),
        ("Pareto", summary.get("n_pareto", "-")),
        ("Sampling conf.", summary.get("confidence", "-")),
        ("Knob set", summary.get("knob_set", "-")),
    ])
    if obj_label:
        ui.label(f"Objectives: {obj_label} · seed={summary.get('seed', '-')}").classes(
            "text-caption text-grey q-mb-sm"
        )
