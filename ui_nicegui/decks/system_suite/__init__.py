"""System Suite deck — NiceGUI workflow UX on frozen Point Designer truth."""
from __future__ import annotations

from typing import Any, Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.system_suite import tabs as suite_tabs
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context
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


def _render_header(session: DesignSession, point_out: Optional[dict[str, Any]]) -> None:
    if not point_out:
        return
    summary = verdict_summary(point_out)
    if not summary.get("loaded"):
        return
    kpi_row([
        ("Verdict", summary["verdict"]),
        ("Dominant", summary["dominant"]),
        (summary["q_label"], ""),
        (summary["nt_label"], ""),
    ])
    subs = summary.get("subsystems") or {}
    with ui.row().classes("gap-2 q-mt-xs flex-wrap"):
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant"):
            status = subs.get(name, "pass")
            color = {"pass": "green", "fail": "red"}.get(status, "grey")
            ui.badge(name.title(), color=color).props("outline")
    render_overlay_status_panel(point_out)
    if not summary.get("parity_aligned", True):
        ui.label(
            f"Constraint pipeline parity: {summary.get('parity_n_mismatch', 0)} pass mismatches "
            f"({summary.get('parity_n_gov', 0)} gov / {summary.get('parity_n_ledger', 0)} ledger)."
        ).classes("text-caption text-orange q-mt-xs")


@ui.refreshable
def _render_tab_content(session: DesignSession, ctx: suite_tabs.SuiteContext) -> None:
    step = normalize_suite_tab(session.suite_workflow_step)
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


def render_system_suite(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "suite")
    ui.label("System Suite").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("suite", default_open=False)

    art, point_inp, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer → Evaluate Point** first to populate System Suite diagnostics.",
            kind="info",
        )
        return

    try:
        from tools.system_suite import (
            lifetime_and_fuel_overlay,
            ops_availability_overlay,
            power_closure_overlay,
            thermal_network_diagnostics_client,
            trajectory_diagnostics_client,
        )
    except Exception as exc:
        ui.label(f"System Suite import failed: {exc}").classes("text-negative")
        return

    ctx = suite_tabs.SuiteContext(
        session=session,
        artifact=art,
        point_inp=point_inp,
        point_out=point_out,
        overlays={
            "power_closure_overlay": power_closure_overlay,
            "ops_availability_overlay": ops_availability_overlay,
            "thermal_network_diagnostics_client": thermal_network_diagnostics_client,
            "trajectory_diagnostics_client": trajectory_diagnostics_client,
            "lifetime_and_fuel_overlay": lifetime_and_fuel_overlay,
        },
    )

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label("Point evaluation loaded").classes("text-caption text-positive")
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
    step = session.suite_workflow_step

    ui.toggle(
        SUITE_TABS,
        value=step,
        on_change=lambda e: (
            setattr(session, "suite_workflow_step", normalize_suite_tab(str(e.value))),
            _render_tab_content.refresh(),
        ),
    ).classes("w-full q-mb-xs")
    ui.label(TAB_HELP.get(normalize_suite_tab(session.suite_workflow_step), "")).classes(
        "text-caption text-grey q-mb-md"
    )

    _render_tab_content(session, ctx)
