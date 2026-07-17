"""Reactor Design Forge — 4-tab NiceGUI workflow (complete migration)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.deck_gate import pd_prerequisite_gate
from ui_nicegui.components.workflow_cta import render_goto_setup_button
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.reactor_design_forge import (
    capsules,
    instruments,
    intent_compiler,
    machine_finder,
    setup_panel,
    verdict,
    workbench,
)
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.baseline_kpi_caption import baseline_kpi_caption, baseline_kpi_classes
from ui_nicegui.lib.forge_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    FORGE_TABS,
    TAB_HELP,
    normalize_forge_tab,
    teaching_banner,
)
from ui_nicegui.lib.forge_helpers import summarize_forge_state
from ui_nicegui.lib.forge_machine_finder_helpers import summarize_workbench_run
from ui_nicegui.session import DesignSession

_LEGACY_FROM_TAB = {
    "1 · Compile Intent": "Intent Compiler",
    "2 · Setup & Search": "Machine Finder",
    "3 · Workbench": "Machine Finder",
    "4 · Instruments": "Machine Finder",
    "5 · Capsules & Export": "Capsules",
}


def _refresh_all() -> None:
    _render_dashboard.refresh()
    _render_tab_body.refresh()


def _set_forge_review_mode(session: DesignSession, value: bool) -> None:
    session.forge_review_mode = bool(value)
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()
    _render_tab_body.refresh()


def _sync_legacy_deck(session: DesignSession, tab: str) -> None:
    session.forge_deck = _LEGACY_FROM_TAB.get(tab, "Intent Compiler")


def render_reactor_design_forge(session: DesignSession) -> None:
    ui.label("Reactor Design Forge").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("forge", default_open=False)

    art, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        pd_prerequisite_gate(
            "Run **Point Designer → Evaluate Point** first — Forge uses that baseline.",
        )
        return

    from ui_nicegui.lib.session_store import get_cached_verdict_summary

    _vs = get_cached_verdict_summary(session, point_out)
    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label(baseline_kpi_caption(point_out, artifact=art, verdict=_vs)).classes(
            baseline_kpi_classes(point_out, verdict=_vs)
        )
        with ui.row().classes("gap-4 flex-wrap"):
            ui.switch(
                "Guided mode",
                value=session.forge_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "forge_teaching_mode", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.forge_expert_view,
                on_change=lambda e: (
                    setattr(session, "forge_expert_view", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )
            ui.switch(
                "Review Mode (locks run controls)",
                value=session.forge_review_mode,
                on_change=lambda e: _set_forge_review_mode(session, bool(e.value)),
            )

    from ui_nicegui.lib.pd_intent_policy import policy_caption

    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-xs")

    if session.forge_review_mode:
        ui.label("Review Mode: search/compile controls locked; inspect archives and export only.").classes(
            "text-orange q-mb-sm"
        )

    _render_dashboard(session)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.forge_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.forge_teaching_mode:
            session.forge_workflow_step = tab
            _sync_legacy_deck(session, tab)
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to do?",
        value=session.forge_decision_state
        if session.forge_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.forge_workflow_step = normalize_forge_tab(session.forge_workflow_step)
    _sync_legacy_deck(session, session.forge_workflow_step)

    ui.toggle(
        FORGE_TABS,
        value=session.forge_workflow_step,
        on_change=lambda e: (
            setattr(session, "forge_workflow_step", normalize_forge_tab(str(e.value))),
            _sync_legacy_deck(session, normalize_forge_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")

    help_text = TAB_HELP.get(normalize_forge_tab(session.forge_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_tab_body(session)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = summarize_forge_state(session.forge_intent_compiler_last, session.forge_last_audit)
    wb = summarize_workbench_run(session.forge_workbench_run)
    if wb.get("loaded"):
        summary = {
            **summary,
            "loaded": True,
            "workbench_loaded": True,
            "audit_verdict": f"Archive {wb.get('n_feasible_archive')}/{wb.get('n_archive')} feasible",
            "dominant": wb.get("top_blocker") or wb.get("dominant_resistance") or summary.get("dominant"),
        }
    verdict.render_forge_dashboard(summary)


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_forge_tab(session.forge_workflow_step)
    open_setup = session.forge_teaching_mode and not session.forge_expert_view
    review = session.forge_review_mode

    if step == "1 · Compile Intent":
        setup_panel.render_setup_panel(default_open=open_setup)
        ui.separator().classes("q-my-sm")
        if review:
            ui.label("Review Mode: compile disabled.").classes("text-caption text-grey")
        else:
            intent_compiler.render_intent_compiler(session, on_complete=_refresh_all)
    elif step == "2 · Setup & Search":
        setup_panel.render_setup_panel(default_open=open_setup)
        ui.separator().classes("q-my-sm")
        machine_finder.render_machine_finder(
            session,
            review_mode=review,
            flat=open_setup,
            on_complete=_refresh_all,
        )
    elif step == "3 · Workbench":
        workbench.render_forge_workbench(
            session,
            review_mode=review,
            on_complete=_refresh_all,
        )
    elif step == "4 · Instruments":
        instruments.render_instruments_tab(
            session,
            review_mode=review,
            on_complete=_refresh_all,
        )
    elif step == "5 · Capsules & Export":
        capsules.render_capsules(session, on_complete=_refresh_all)
