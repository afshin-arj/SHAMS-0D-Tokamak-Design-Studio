"""Pareto Lab deck — 5-tab workflow on frozen feasible-only frontier (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.pareto_lab import (
    controls,
    explore,
    export_handoff,
    external,
    interpret,
    setup_panel,
    verdict,
)
from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.pareto_labels import (
    ALL_EXTERNAL as EXTERNAL_DECKS,
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    EXTERNAL_GROUPS,
    PARETO_LOCK_LINE,
    PARETO_TABS,
    TAB_HELP,
    normalize_pareto_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def _refresh_all() -> None:
    _render_dashboard.refresh()
    _render_tab_body.refresh()


def render_pareto_lab(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "pareto")
    ui.label("Pareto Lab").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    ui.markdown(PARETO_LOCK_LINE).classes("text-body2 q-mb-sm")
    render_mode_scope("pareto", default_open=False)

    _, _, point_out = get_point_artifact_triple(session)
    has_eval = isinstance(point_out, dict) and bool(point_out)
    if not has_eval:
        ui.badge(
            "No Point Designer evaluation — using session baseline inputs",
            color="orange",
        ).props("outline").classes("q-mb-sm")
    else:
        with ui.row().classes("w-full items-center justify-between q-mb-sm"):
            ui.label("Point evaluation loaded").classes("text-caption text-positive")

    with ui.row().classes("w-full items-center justify-end gap-4 q-mb-sm"):
        ui.switch(
            "Guided mode",
            value=session.pareto_teaching_mode,
            on_change=lambda e: (
                setattr(session, "pareto_teaching_mode", bool(e.value)),
                _render_tab_body.refresh(),
            ),
        )
        ui.switch(
            "Expert view",
            value=session.pareto_expert_view,
            on_change=lambda e: (
                setattr(session, "pareto_expert_view", bool(e.value)),
                _render_tab_body.refresh(),
            ),
        )

    _render_dashboard(session)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.pareto_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.pareto_teaching_mode:
            session.pareto_workflow_step = tab
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to learn?",
        value=session.pareto_decision_state
        if session.pareto_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.pareto_workflow_step = normalize_pareto_tab(session.pareto_workflow_step)
    ui.toggle(
        PARETO_TABS,
        value=session.pareto_workflow_step,
        on_change=lambda e: (
            setattr(session, "pareto_workflow_step", normalize_pareto_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_pareto_tab(session.pareto_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_tab_body(session)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = None
    if isinstance(session.pareto_last, dict):
        summary = session.pareto_last.get("summary")
    verdict.render_frontier_dashboard(summary)


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_pareto_tab(session.pareto_workflow_step)
    open_setup = session.pareto_teaching_mode and not session.pareto_expert_view

    if step == "1 · Setup & Run":
        setup_panel.render_setup_panel(
            default_open=open_setup,
            on_restore=lambda art: (setattr(session, "pareto_last", art), _refresh_all()),
        )
        ui.separator().classes("q-my-sm")
        controls.render_pareto_controls(
            session,
            flat=open_setup,
            on_complete=_refresh_all,
        )
    elif step == "2 · Explore Frontier":
        if not isinstance(session.pareto_last, dict):
            empty_state("Run a Pareto study on **Setup & Run** first.", kind="info")
            ui.button("Go to Setup & Run", icon="settings", on_click=lambda: (
                setattr(session, "pareto_workflow_step", "1 · Setup & Run"),
                _render_tab_body.refresh(),
            )).props("outline")
            return
        explore.render_explore_tab(session, session.pareto_last, on_update=_render_tab_body.refresh)
    elif step == "3 · Interpret & Audit":
        if not isinstance(session.pareto_last, dict):
            empty_state("Run a Pareto study first.", kind="info")
            return
        interpret.render_interpret_tab(session, session.pareto_last)
    elif step == "4 · Export & Handoff":
        export_handoff.render_export_tab(
            session,
            session.pareto_last if isinstance(session.pareto_last, dict) else None,
            on_restore=_refresh_all,
        )
    elif step == "5 · External Tools":
        _render_external_router(session)


def _render_external_router(session: DesignSession) -> None:
    groups = list(EXTERNAL_GROUPS.keys())
    if session.pareto_external_group not in groups:
        session.pareto_external_group = groups[0]
    tools = EXTERNAL_GROUPS.get(session.pareto_external_group, [])
    if session.pareto_external_tool not in tools:
        session.pareto_external_tool = tools[0] if tools else ""

    grp = ui.select(
        groups,
        label="Tool category",
        value=session.pareto_external_group,
        on_change=lambda e: _on_group_change(session, str(e.value)),
    ).classes("w-full")
    tool = ui.select(
        tools,
        label="External deck",
        value=session.pareto_external_tool,
        on_change=lambda e: setattr(session, "pareto_external_tool", str(e.value)),
    ).classes("w-full q-mb-md")

    def _on_group_change(sess: DesignSession, g: str) -> None:
        sess.pareto_external_group = g
        tlist = EXTERNAL_GROUPS.get(g, [])
        sess.pareto_external_tool = tlist[0] if tlist else ""
        tool.set_options(tlist, value=sess.pareto_external_tool)

    deck = str(session.pareto_external_tool or tool.value)
    if deck:
        external.render_external_deck(session, deck)
    else:
        empty_state("Select an external tool.", kind="info")
