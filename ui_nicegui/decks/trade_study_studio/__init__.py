"""Trade Study Studio deck — 5-tab workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.deck_gate import pd_prerequisite_gate
from ui_nicegui.components.workflow_cta import render_goto_setup_button
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.trade_study_studio import (
    advanced,
    controls,
    explore,
    export_handoff,
    interpret,
    setup_panel,
    verdict,
)
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.baseline_kpi_caption import baseline_kpi_caption, baseline_kpi_classes
from ui_nicegui.lib.navigation import refresh_active_deck
from ui_nicegui.lib.trade_study_helpers import ADVANCED_DECKS, STUDY_SETUP_DECK
from ui_nicegui.lib.trade_study_labels import (
    ADVANCED_GROUPS,
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    TRADE_TABS,
    TAB_HELP,
    normalize_trade_tab,
    normalize_trade_advanced_deck,
    teaching_banner,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.lib.expert_mode import sync_deck_expert_to_helm

__all__ = [
    "ADVANCED_DECKS",
    "STUDY_SETUP_DECK",
    "render_trade_study_studio",
]


def _refresh_all() -> None:
    _render_dashboard.refresh()
    _render_tab_body.refresh()


def render_trade_study_studio(session: DesignSession) -> None:
    ui.label("Trade Study Studio").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("trade", default_open=False)

    art, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        pd_prerequisite_gate(
            "Run **Point Designer → Evaluate Point** first — Trade Study uses that baseline.",
        )
        return

    from ui_nicegui.lib.session_store import get_cached_verdict_summary

    _vs = get_cached_verdict_summary(session, point_out)
    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label(
            baseline_kpi_caption(
                point_out,
                artifact=art,
                verdict=_vs,
                design_intent=str(session.design_intent),
                fuel_mode=str((session.inputs or {}).get("fuel_mode", "DT")),
            )
        ).classes(baseline_kpi_classes(point_out, verdict=_vs))
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.trade_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "trade_teaching_mode", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.trade_expert_view,
                on_change=lambda e: (
                    sync_deck_expert_to_helm(session, bool(e.value), deck_attr="trade_expert_view"),
                    _render_tab_body.refresh(),
                ),
            )

    from ui_nicegui.lib.pd_intent_policy import policy_caption

    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-xs")
    _render_dashboard(session)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.trade_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.trade_teaching_mode:
            session.trade_workflow_step = tab
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to learn?",
        value=session.trade_decision_state
        if session.trade_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.trade_workflow_step = normalize_trade_tab(session.trade_workflow_step)
    ui.toggle(
        TRADE_TABS,
        value=session.trade_workflow_step,
        on_change=lambda e: (
            setattr(session, "trade_workflow_step", normalize_trade_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_trade_tab(session.trade_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_tab_body(session)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = None
    if isinstance(session.trade_last, dict):
        summary = session.trade_last.get("summary")
    verdict.render_study_dashboard(summary, design_intent=str(session.design_intent or ""))


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_trade_tab(session.trade_workflow_step)
    open_setup = session.trade_teaching_mode and not session.trade_expert_view

    if step == "1 · Setup & Run":
        setup_panel.render_setup_panel(default_open=open_setup)
        ui.separator().classes("q-my-sm")
        controls.render_study_controls(
            session,
            flat=open_setup,
            on_complete=_refresh_all,
            on_change=_render_tab_body.refresh,
        )
    elif step == "2 · Explore Results":
        if not isinstance(session.trade_last, dict):
            empty_state("Run a trade study on **Setup & Run** first.", kind="info")
            render_goto_setup_button(
                session, attr="trade_workflow_step", on_refresh=refresh_active_deck
            )
            return
        explore.render_explore_tab(session, session.trade_last, on_update=_render_tab_body.refresh)
    elif step == "3 · Interpret & Families":
        if not isinstance(session.trade_last, dict):
            empty_state("Run a trade study first.", kind="info")
            render_goto_setup_button(
                session, attr="trade_workflow_step", on_refresh=refresh_active_deck
            )
            return
        interpret.render_interpret_tab(session, session.trade_last)
    elif step == "4 · Export & Handoff":
        export_handoff.render_export_tab(
            session,
            session.trade_last if isinstance(session.trade_last, dict) else None,
            on_restore=_refresh_all,
        )
    elif step == "5 · Advanced Tools":
        _render_advanced_router(session)


def _render_advanced_router(session: DesignSession) -> None:
    groups = list(ADVANCED_GROUPS.keys())
    if session.trade_advanced_group not in groups:
        session.trade_advanced_group = groups[0]
    decks = ADVANCED_GROUPS.get(session.trade_advanced_group, [])
    if session.trade_advanced_deck not in decks:
        session.trade_advanced_deck = normalize_trade_advanced_deck(session.trade_advanced_deck)
        if session.trade_advanced_deck not in decks:
            session.trade_advanced_deck = decks[0] if decks else ""

    @ui.refreshable
    def _deck_body() -> None:
        deck = str(session.trade_advanced_deck or "")
        if deck:
            advanced.render_advanced_deck(session, deck)
        else:
            empty_state("Select an advanced tool.", kind="info")

    def _on_group_change(sess: DesignSession, g: str) -> None:
        sess.trade_advanced_group = g
        dlist = ADVANCED_GROUPS.get(g, [])
        sess.trade_advanced_deck = dlist[0] if dlist else ""
        deck_sel.set_options(dlist, value=sess.trade_advanced_deck)
        _deck_body.refresh()

    def _on_deck_change(e) -> None:
        session.trade_advanced_deck = str(e.value)
        _deck_body.refresh()

    ui.select(
        groups,
        label="Tool category",
        value=session.trade_advanced_group,
        on_change=lambda e: _on_group_change(session, str(e.value)),
    ).classes("w-full")
    deck_sel = ui.select(
        decks,
        label="Advanced deck",
        value=session.trade_advanced_deck,
        on_change=_on_deck_change,
    ).classes("w-full q-mb-md")

    _deck_body()
