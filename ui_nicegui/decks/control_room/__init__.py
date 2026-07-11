"""Control Room deck — 6-section workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.control_room import artifacts, chronicle, constitution, diagnostics, orientation, provenance, verdict
from ui_nicegui.lib.control_room_helpers import governance_summary
from ui_nicegui.lib.control_room_labels import (
    CR_WORKFLOW_TABS,
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    TAB_HELP,
    normalize_cr_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession

from ui_nicegui.lib.control_room_helpers import CR_SECTIONS

# Legacy section names ported from Streamlit (see test_nicegui_phase18).
_PORTED = frozenset(CR_SECTIONS)

_SECTION_RENDERERS = {
    "1 · Orient": orientation.render_orientation,
    "2 · Constitution": constitution.render_constitution,
    "3 · Provenance": provenance.render_provenance,
    "4 · Artifacts": artifacts.render_artifacts,
    "5 · Diagnostics": diagnostics.render_diagnostics,
    "6 · Chronicle": chronicle.render_chronicle,
}

_LEGACY_TO_WORKFLOW = {
    "Orientation": "1 · Orient",
    "Constitution": "2 · Constitution",
    "Provenance": "3 · Provenance",
    "Artifacts": "4 · Artifacts",
    "Diagnostics": "5 · Diagnostics",
    "Chronicle": "6 · Chronicle",
}


def _sync_section(session: DesignSession, tab: str) -> None:
    session.cr_workflow_step = normalize_cr_tab(tab)
    session.cr_section = _LEGACY_TO_WORKFLOW.get(session.cr_workflow_step, "Orientation")


def render_control_room(session: DesignSession) -> None:
    ui.label("Control Room").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")

    summary = governance_summary(session)
    verdict.render_governance_verdict(summary)

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label(f"SHAMS {summary.get('version', '')} · {summary.get('active_deck', '')}").classes("text-caption text-grey")
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.cr_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "cr_teaching_mode", bool(e.value)),
                    _render_section.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.cr_expert_view,
                on_change=lambda e: (
                    setattr(session, "cr_expert_view", bool(e.value)),
                    _render_section.refresh(),
                ),
            )

    def _on_decision(e) -> None:
        state = str(e.value)
        session.cr_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.cr_teaching_mode:
            _sync_section(session, tab)
            _render_section.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to do?",
        value=session.cr_decision_state if session.cr_decision_state in DECISION_STATES else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner and not session.cr_expert_view:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    step = normalize_cr_tab(session.cr_workflow_step or session.cr_section)
    if session.cr_workflow_step != step:
        session.cr_workflow_step = step
    _sync_section(session, step)

    ui.toggle(
        CR_WORKFLOW_TABS,
        value=session.cr_workflow_step,
        on_change=lambda e: (
            _sync_section(session, str(e.value)),
            _render_section.refresh(),
        ),
    ).classes("w-full")

    help_text = TAB_HELP.get(session.cr_workflow_step, "")
    if help_text and not session.cr_expert_view:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_section(session)


@ui.refreshable
def _render_section(session: DesignSession) -> None:
    fn = _SECTION_RENDERERS.get(session.cr_workflow_step)
    if fn:
        fn(session)
