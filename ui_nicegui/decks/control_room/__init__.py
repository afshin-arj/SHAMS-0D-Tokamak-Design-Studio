"""Control Room deck — 6-section workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.control_room import artifacts, chronicle, constitution, diagnostics, orientation, provenance, verdict
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

from ui_nicegui.lib.control_room_helpers import CR_SECTIONS, read_version

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
    render_mode_scope("governance", default_open=False)

    verdict.render_governance_verdict_live(session)

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        _ver = read_version()
        ver_label = _ver if str(_ver).startswith("v") else f"v{_ver}"
        ui.label(f"SHAMS {ver_label} · {session.active_deck}").classes("text-caption text-grey")
        _render_mode_switches(session)

    _render_decision_chrome(session)

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
def _render_mode_switches(session: DesignSession) -> None:
    """Guided and Expert are mutually exclusive — refresh widgets when either flips."""

    def _on_guided(e) -> None:
        session.cr_teaching_mode = bool(e.value)
        if session.cr_teaching_mode:
            session.cr_expert_view = False
        _render_mode_switches.refresh()
        _render_decision_chrome.refresh()
        _render_section.refresh()

    def _on_expert(e) -> None:
        session.cr_expert_view = bool(e.value)
        if session.cr_expert_view:
            session.cr_teaching_mode = False
        _render_mode_switches.refresh()
        _render_decision_chrome.refresh()
        _render_section.refresh()

    with ui.row().classes("gap-4"):
        ui.switch("Guided mode", value=bool(session.cr_teaching_mode), on_change=_on_guided)
        ui.switch("Expert view", value=bool(session.cr_expert_view), on_change=_on_expert)


@ui.refreshable
def _render_decision_chrome(session: DesignSession) -> None:
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


@ui.refreshable
def _render_section(session: DesignSession) -> None:
    fn = _SECTION_RENDERERS.get(session.cr_workflow_step)
    if fn:
        fn(session)
