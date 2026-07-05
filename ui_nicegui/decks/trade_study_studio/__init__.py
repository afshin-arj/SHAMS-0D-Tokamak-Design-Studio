"""Trade Study Studio deck — 5-tab workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
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
from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context
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

__all__ = [
    "ADVANCED_DECKS",
    "STUDY_SETUP_DECK",
    "render_trade_study_studio",
]


def _refresh_all() -> None:
    _render_dashboard.refresh()
    _render_tab_body.refresh()


def render_trade_study_studio(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "trade")
    ui.label("Trade Study Studio").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("trade", default_open=False)

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer → Evaluate Point** first — Trade Study uses that baseline.",
            kind="info",
        )
        return

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label("Point evaluation loaded").classes("text-caption text-positive")
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
                    setattr(session, "trade_expert_view", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )

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
    verdict.render_study_dashboard(summary)


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_trade_tab(session.trade_workflow_step)
    open_setup = session.trade_teaching_mode and not session.trade_expert_view

    if step == "1 · Setup & Run":
        setup_panel.render_setup_panel(default_open=open_setup)
        ui.separator().classes("q-my-sm")
        controls.render_study_controls(session, flat=open_setup, on_complete=_refresh_all)
    elif step == "2 · Explore Results":
        if not isinstance(session.trade_last, dict):
            empty_state("Run a trade study on **Setup & Run** first.", kind="info")
            return
        explore.render_explore_tab(session, session.trade_last, on_update=_render_tab_body.refresh)
    elif step == "3 · Interpret & Families":
        if not isinstance(session.trade_last, dict):
            empty_state("Run a trade study first.", kind="info")
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

    grp = ui.select(
        groups,
        label="Tool category",
        value=session.trade_advanced_group,
        on_change=lambda e: _on_group_change(session, str(e.value)),
    ).classes("w-full")
    deck_sel = ui.select(
        decks,
        label="Advanced deck",
        value=session.trade_advanced_deck,
        on_change=lambda e: setattr(session, "trade_advanced_deck", str(e.value)),
    ).classes("w-full q-mb-md")

    def _on_group_change(sess: DesignSession, g: str) -> None:
        sess.trade_advanced_group = g
        dlist = ADVANCED_GROUPS.get(g, [])
        sess.trade_advanced_deck = dlist[0] if dlist else ""
        deck_sel.set_options(dlist, value=sess.trade_advanced_deck)

    deck = str(session.trade_advanced_deck or deck_sel.value)
    if deck:
        advanced.render_advanced_deck(session, deck)
    else:
        empty_state("Select an advanced tool.", kind="info")
