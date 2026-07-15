"""System Suite deck — NiceGUI workflow UX on frozen Point Designer truth."""
from __future__ import annotations

from typing import Any, Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.deck_gate import pd_prerequisite_gate
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.decks.system_suite import tabs as suite_tabs
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.pd_hero_kpis import hero_kpi_cells
from ui_nicegui.lib.pd_parity_helpers import no_solution_atlas_summary
from ui_nicegui.lib.suite_helpers import authority_version_badges
from ui_nicegui.lib.suite_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    SUITE_TABS,
    TAB_HELP,
    normalize_suite_tab,
    teaching_banner,
)
from ui_nicegui.lib.suite_overlay_helpers import render_overlay_status_panel
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession

_SUITE_OVERLAYS: Optional[dict[str, Any]] = None


def _suite_overlays() -> dict[str, Any]:
    """Cache tools.system_suite imports — avoid remount latency on every deck switch."""
    global _SUITE_OVERLAYS
    if _SUITE_OVERLAYS is not None:
        return _SUITE_OVERLAYS
    from tools.system_suite import (
        lifetime_and_fuel_overlay,
        ops_availability_overlay,
        power_closure_overlay,
        thermal_network_diagnostics_client,
        trajectory_diagnostics_client,
    )

    _SUITE_OVERLAYS = {
        "power_closure_overlay": power_closure_overlay,
        "ops_availability_overlay": ops_availability_overlay,
        "thermal_network_diagnostics_client": thermal_network_diagnostics_client,
        "trajectory_diagnostics_client": trajectory_diagnostics_client,
        "lifetime_and_fuel_overlay": lifetime_and_fuel_overlay,
    }
    return _SUITE_OVERLAYS


def _fmt_num(x, *, digits: int = 3) -> str:
    try:
        v = float(x)
        if v != v:
            return "n/a"
        return f"{v:.{digits}g}"
    except (TypeError, ValueError):
        return "n/a"


def _render_header(session: DesignSession, point_out: Optional[dict[str, Any]]) -> None:
    if not point_out:
        return
    summary = verdict_summary(point_out)
    if not summary.get("loaded"):
        return
    detail = f"Dominant: {summary['dominant']}"
    verdict_banner(summary["verdict"], detail=detail)

    fuel = str((session.inputs or {}).get("fuel_mode", "DT"))
    cells = hero_kpi_cells(
        point_out,
        summary,
        design_intent=session.design_intent,
        fuel_mode=fuel,
    )
    kpi_row([(c.label, c.display) for c in cells[:4]])

    beta = point_out.get("betaN", point_out.get("beta_N"))
    fg = point_out.get("fG", point_out.get("greenwald_fraction"))
    q95 = point_out.get("q95")
    kpi_row([
        ("β_N", _fmt_num(beta)),
        ("f_G", _fmt_num(fg)),
        ("q95", _fmt_num(q95)),
    ])

    subs = summary.get("subsystems") or {}
    with ui.row().classes("gap-2 q-mt-xs flex-wrap"):
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant"):
            status = subs.get(name, "pass")
            color = {"pass": "green", "fail": "red", "warn": "orange"}.get(status, "grey")
            ui.badge(name.title(), color=color).props("outline")
    badges = authority_version_badges(point_out)
    if badges:
        with ui.row().classes("gap-1 q-mt-xs flex-wrap"):
            for b in badges:
                ui.badge(b, color="blue-grey").props("outline dense")
    render_overlay_status_panel(point_out)
    if not summary.get("feasible"):
        atlas = no_solution_atlas_summary(point_out, design_intent=session.design_intent)
        ui.label(
            f"Mechanism: {atlas.get('dominant_mechanism', '-')} · "
            f"Constraint: {atlas.get('dominant_constraint', '-')}"
        ).classes("text-caption text-orange q-mt-xs")
    if not summary.get("parity_aligned", True):
        ui.label(
            f"Constraint pipeline parity: {summary.get('parity_n_mismatch', 0)} pass mismatches "
            f"({summary.get('parity_n_gov', 0)} gov / {summary.get('parity_n_ledger', 0)} ledger)."
        ).classes("text-caption text-orange q-mt-xs")


@ui.refreshable
def _render_tab_content(session: DesignSession, ctx: suite_tabs.SuiteContext) -> None:
    step = normalize_suite_tab(session.suite_workflow_step)
    try:
        if step == "1 · Plant & Power":
            suite_tabs.render_tab_plant_power(ctx)
        elif step == "2 · Operations & Thermal":
            suite_tabs.render_tab_ops_thermal(ctx)
        elif step == "3 · Lifetime & Regimes":
            suite_tabs.render_tab_lifetime_regimes(ctx)
        elif step == "4 · Envelope Robustness":
            suite_tabs.render_tab_envelope_robustness(ctx)
        elif step == "5 · Scenarios & Exports":
            suite_tabs.render_tab_scenarios_exports(ctx)
        else:
            empty_state(f"Unknown System Suite tab: {step}", kind="warn")
    except Exception as exc:
        empty_state(f"System Suite tab failed to render: {exc}", kind="error")
        ui.label(str(exc)).classes("text-negative text-caption")


def render_system_suite(session: DesignSession) -> None:
    ui.label("System Suite").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    ui.markdown(
        "**System Suite** — read-only L1 engineering overlays on your Point Designer evaluation. "
        "This is **not Systems Mode** (Monte Carlo precheck / Newton solver)."
    ).classes("text-caption q-mb-sm")
    render_mode_scope("suite", default_open=False)

    art, point_inp, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        pd_prerequisite_gate(
            "Run **Point Designer → Evaluate Point** first to populate System Suite diagnostics.",
        )
        return

    try:
        overlays = _suite_overlays()
    except Exception as exc:
        ui.label(f"System Suite import failed: {exc}").classes("text-negative")
        return

    ctx = suite_tabs.SuiteContext(
        session=session,
        artifact=art,
        point_inp=point_inp,
        point_out=point_out,
        overlays=overlays,
    )

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ts = session.pd_last_run_ts
        ts_label = f"eval t={int(ts)}" if isinstance(ts, (int, float)) and ts else "loaded"
        ui.label(f"Point evaluation {ts_label}").classes("text-caption text-positive")
        if session.suite_running:
            ui.badge("Suite job running", color="orange").props("outline")
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.suite_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "suite_teaching_mode", bool(e.value)),
                    _render_tab_content.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.suite_expert_view,
                on_change=lambda e: (
                    setattr(session, "suite_expert_view", bool(e.value)),
                    _render_tab_content.refresh(),
                ),
            )

    _render_header(session, point_out)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.suite_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.suite_teaching_mode:
            session.suite_workflow_step = tab
            _render_tab_help.refresh()
            _render_tab_content.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you reviewing?",
        value=session.suite_decision_state
        if session.suite_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.suite_workflow_step = normalize_suite_tab(session.suite_workflow_step)

    ui.toggle(
        SUITE_TABS,
        value=session.suite_workflow_step,
        on_change=lambda e: (
            setattr(session, "suite_workflow_step", normalize_suite_tab(str(e.value))),
            _render_tab_help.refresh(),
            _render_tab_content.refresh(),
        ),
    ).classes("w-full q-mb-xs")
    _render_tab_help(session)

    _render_tab_content(session, ctx)


@ui.refreshable
def _render_tab_help(session: DesignSession) -> None:
    ui.label(TAB_HELP.get(normalize_suite_tab(session.suite_workflow_step), "")).classes(
        "text-caption text-grey q-mb-md"
    )
