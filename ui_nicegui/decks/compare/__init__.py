"""Compare deck — 5-tab workflow on frozen evaluator (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.compare import (
    constraints_panel,
    export_panel,
    inputs_structure,
    metrics,
    setup,
    verdict,
)
from ui_nicegui.lib.compare_helpers import summarize_comparison
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.compare_labels import (
    COMPARE_TABS,
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    TAB_HELP,
    normalize_compare_tab,
    teaching_banner,
)
from ui_nicegui.lib.deck_busy_guard import COMPARE_RUNNING_ATTRS, refresh_tab_if_idle
from ui_nicegui.session import DesignSession
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.expert_mode import sync_deck_expert_to_helm
from ui_nicegui.lib.teaching_mode import sync_deck_guided_to_helm


def _refresh_all() -> None:
    _render_verdict.refresh()
    _render_workflow.refresh()
    _render_tab_body.refresh()
    # Slot loads use refresh=False to avoid full remount lag — still sync Helm posture.
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()


def render_compare(session: DesignSession) -> None:
    ui.label("Compare").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("compare", default_open=False)

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        ui.badge(
            "No Point Designer evaluation in session — you can still load A & B from JSON",
            color="orange",
        ).props("outline").classes("q-mb-sm")
        ui.label(
            "Tip: anchor a point in Point Designer when comparing against the live session; "
            "artifact-only review works from tab 1 without a session evaluation."
        ).classes("text-caption text-grey q-mb-sm")
        ui.button(
            "Open Point Designer",
            icon="design_services",
            on_click=lambda: switch_deck("Point Designer"),
        ).props("outline dense").classes("q-mb-sm")

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        art_a, art_b = setup.resolve_artifacts(session)
        if art_a and art_b:
            ui.label("Both slots loaded — ready to compare").classes("text-caption text-positive")
        elif art_a or art_b:
            ui.label("One slot loaded — load the other on tab 1").classes("text-caption text-orange")
        else:
            ui.label("Load artifacts on tab 1 to begin").classes("text-caption text-grey")
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.cmp_teaching_mode,
                on_change=lambda e: (
                    sync_deck_guided_to_helm(session, bool(e.value), deck_attr="cmp_teaching_mode"),
                    refresh_tab_if_idle(
                        session,
                        running_attrs=COMPARE_RUNNING_ATTRS,
                        refresh=lambda: (_render_workflow.refresh(), _render_tab_body.refresh()),
                        job_label="Compare handoff",
                    ),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.cmp_expert_view,
                on_change=lambda e: (
                    sync_deck_expert_to_helm(session, bool(e.value), deck_attr="cmp_expert_view"),
                    refresh_tab_if_idle(
                        session,
                        running_attrs=COMPARE_RUNNING_ATTRS,
                        refresh=_render_tab_body.refresh,
                        job_label="Compare handoff",
                    ),
                ),
            )

    _render_verdict(session)
    _render_workflow(session)
    _render_tab_body(session)


@ui.refreshable
def _render_workflow(session: DesignSession) -> None:
    def _on_decision(e) -> None:
        state = str(e.value)
        session.cmp_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.cmp_teaching_mode:
            session.cmp_workflow_step = tab
            _render_workflow.refresh()
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to learn?",
        value=session.cmp_decision_state
        if session.cmp_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.cmp_workflow_step = normalize_compare_tab(session.cmp_workflow_step)
    ui.toggle(
        COMPARE_TABS,
        value=session.cmp_workflow_step,
        on_change=lambda e: (
            setattr(session, "cmp_workflow_step", normalize_compare_tab(str(e.value))),
            refresh_tab_if_idle(
                session,
                running_attrs=COMPARE_RUNNING_ATTRS,
                refresh=_render_tab_body.refresh,
                job_label="Compare handoff",
            ),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_compare_tab(session.cmp_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")


@ui.refreshable
def _render_verdict(session: DesignSession) -> None:
    art_a, art_b = setup.resolve_artifacts(session)
    if art_a and art_b:
        summary = summarize_comparison(art_a, art_b)
    else:
        summary = None
        if session.cmp_use_slot_a and not session.cmp_slot_a:
            empty_state(
                "Slot A is selected but empty — load from Point Designer or upload JSON.",
                kind="warn",
            )
        if session.cmp_use_slot_b and not session.cmp_slot_b:
            empty_state(
                "Slot B is selected but empty — load from Point Designer or upload JSON.",
                kind="warn",
            )
    verdict.render_compare_verdict(summary, session=session)


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_compare_tab(session.cmp_workflow_step)
    art_a, art_b = setup.resolve_artifacts(session)
    both = bool(art_a and art_b)

    if step == "1 · Load A & B":
        setup.render_setup_panel(session, on_change=_refresh_all)
        return

    if not both:
        empty_state(
            "Load artifacts into **both slots** on tab 1 before exploring deltas.",
            kind="info",
        )
        from ui_nicegui.components.workflow_cta import render_goto_setup_button

        render_goto_setup_button(
            session,
            attr="cmp_workflow_step",
            step="1 · Load A & B",
            label="Go to Load A & B",
            on_refresh=_refresh_all,
        )
        return

    if step == "2 · Performance":
        metrics.render_metrics_panel(session, art_a, art_b)
    elif step == "3 · Constraints":
        constraints_panel.render_constraints_panel(art_a, art_b)
    elif step == "4 · Inputs & Structure":
        inputs_structure.render_inputs_structure_panel(art_a, art_b)
    elif step == "5 · Export":
        export_panel.render_export_panel(session, art_a, art_b)
