"""Scan Lab deck — 4-tab workflow on frozen cartography (NiceGUI complete)."""
from __future__ import annotations

from typing import Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.scan_lab import (
    cartography,
    deep_maps,
    export_archive,
    insights,
    orientation,
    verdict,
    workbench,
)
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.scan_archive_helpers import probe_scan_imports
from ui_nicegui.lib.scan_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    QUICK_JUMP,
    SCAN_TABS,
    TAB_HELP,
    normalize_scan_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def _refresh_all() -> None:
    _render_verdict.refresh()
    _render_tab_body.refresh()


def render_scan_lab(session: DesignSession) -> None:
    ui.label("Scan Lab").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("scan", default_open=False)

    errs = session.scan_import_errors
    if errs is None:
        errs = probe_scan_imports()
        session.scan_import_errors = errs
    if errs and not session.scan_expert_view:
        with ui.expansion("Import warnings", icon="warning").classes("w-full q-mb-sm"):
            for msg in errs:
                ui.label(msg).classes("text-caption text-orange")

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer → Evaluate Point** first — Scan Lab uses that baseline.",
            kind="info",
        )
        return

    with ui.row().classes("w-full items-center justify-between q-mb-sm flex-wrap"):
        q = point_out.get("Q_DT_eqv", point_out.get("Q"))
        h98 = point_out.get("H98")
        pnet = point_out.get("P_e_net_MW")
        baseline_bits = []
        if q is not None:
            baseline_bits.append(f"Q≈{q}")
        if h98 is not None:
            baseline_bits.append(f"H98≈{h98}")
        if pnet is not None:
            baseline_bits.append(f"P_net≈{pnet} MW")
        cap = "Point evaluation loaded"
        if baseline_bits:
            cap += f" ({', '.join(str(b) for b in baseline_bits[:3])})"
        ui.label(cap).classes("text-caption text-positive")
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.scan_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "scan_teaching_mode", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.scan_expert_view,
                on_change=lambda e: (
                    setattr(session, "scan_expert_view", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )

    _render_verdict(session)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.scan_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.scan_teaching_mode:
            session.scan_workflow_step = tab
            _apply_quick_jump(session, tab)
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to learn?",
        value=session.scan_decision_state
        if session.scan_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    with ui.row().classes("w-full items-end gap-2 q-mb-xs"):
        ui.input(
            "Quick jump (D/F/I/C)",
            value="",
            on_change=lambda e: _handle_quick_jump(session, str(e.value or "").strip().upper()),
        ).props("dense clearable").classes("flex-none").style("max-width: 180px")
        ui.label("D=map · F=interpret · I=compare intents · C=causality").classes(
            "text-caption text-grey"
        )

    session.scan_workflow_step = normalize_scan_tab(session.scan_workflow_step)
    step = session.scan_workflow_step
    ui.toggle(
        SCAN_TABS,
        value=step,
        on_change=lambda e: (
            setattr(session, "scan_workflow_step", normalize_scan_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_scan_tab(session.scan_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_tab_body(session)


def _handle_quick_jump(session: DesignSession, cmd: str) -> None:
    if cmd not in QUICK_JUMP:
        return
    tab, extra = QUICK_JUMP[cmd]
    session.scan_workflow_step = tab
    session.scan_view_mode = cmd
    if extra == "Dominance (blocking)":
        session.scan_wb_view = extra
    elif extra == "causality":
        session.scan_local_insight = "Causality trace"
    elif cmd == "I":
        session.scan_wb_compare_intents = True
    _render_tab_body.refresh()


def _apply_quick_jump(session: DesignSession, tab: str) -> None:
    cmd = str(session.scan_view_mode or "").upper()
    if cmd in QUICK_JUMP:
        _handle_quick_jump(session, cmd)


@ui.refreshable
def _render_verdict(session: DesignSession) -> None:
    verdict.render_scan_verdict(session.scan_cartography_report)


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_scan_tab(session.scan_workflow_step)
    open_orientation = session.scan_teaching_mode and not session.scan_expert_view

    if step == "1 · Setup & Run":
        from ui_nicegui.decks.scan_lab.governance_ui import render_governance_panel

        render_governance_panel(session, session.scan_cartography_report if isinstance(session.scan_cartography_report, dict) else None)
        orientation.render_orientation_panel(session, default_open=open_orientation)
        ui.separator().classes("q-my-sm")
        cartography.render_cartography_controls(
            session,
            on_scan_complete=_refresh_all,
        )
    elif step == "2 · Map & Probe":
        rep = session.scan_cartography_report
        if not isinstance(rep, dict):
            empty_state("Run a cartography scan on **Setup & Run** first.", kind="info")
            return
        workbench.render_workbench(session, rep, on_update=_render_tab_body.refresh)
    elif step == "3 · Interpret":
        rep = session.scan_cartography_report
        if not isinstance(rep, dict):
            empty_state("Run a cartography scan first.", kind="info")
            return
        insights.render_interpret_tab(session, rep, on_update=_render_tab_body.refresh)
        ui.separator().classes("q-my-md")
        from ui_nicegui.decks.scan_lab.slice_diagnostics_ui import render_slice_diagnostics

        render_slice_diagnostics(session, rep, on_update=_render_tab_body.refresh)
        ui.separator().classes("q-my-md")
        deep_maps.render_deep_landscape_maps(session, rep, on_update=_render_tab_body.refresh)
    elif step == "4 · Export & Archive":
        export_archive.render_export_tab(
            session,
            session.scan_cartography_report if isinstance(session.scan_cartography_report, dict) else None,
            on_restore=_refresh_all,
        )
