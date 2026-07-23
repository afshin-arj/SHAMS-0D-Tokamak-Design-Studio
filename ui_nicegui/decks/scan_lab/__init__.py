"""Scan Lab deck — 4-tab workflow on frozen cartography (NiceGUI complete)."""
from __future__ import annotations

from typing import Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.deck_gate import pd_prerequisite_gate
from ui_nicegui.components.workflow_cta import render_goto_setup_button
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
from ui_nicegui.lib.baseline_kpi_caption import baseline_kpi_caption, baseline_kpi_classes
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
from ui_nicegui.lib.expert_mode import sync_deck_expert_to_helm
from ui_nicegui.lib.teaching_mode import sync_deck_guided_to_helm


def _refresh_tab_body_if_idle(session: DesignSession) -> None:
    """Avoid tearing down cartography progress timer while a Scan Lab job is live."""
    if getattr(session, "scan_running", False) or getattr(session, "scan_legacy_running", False):
        ui.notify(
            "Scan Lab job running — wait until it finishes before changing Setup / Guided / Expert.",
            type="warning",
        )
        return
    _render_tab_body.refresh()


def _consume_scan_probe_focus(session: DesignSession) -> None:
    """Apply inbound Scan Lab focus from Pareto/Forge; land on a useful tab."""
    focus = getattr(session, "scan_probe_focus", None)
    if not isinstance(focus, dict):
        return
    has_report = isinstance(getattr(session, "scan_cartography_report", None), dict) or isinstance(
        getattr(session, "scan_cartography_artifact", None), dict
    )
    x_key = focus.get("x_key") or focus.get("x")
    y_key = focus.get("y_key") or focus.get("y")
    if x_key:
        session.scan_cart_x_key = str(x_key)
    if y_key:
        session.scan_cart_y_key = str(y_key)
    if has_report:
        session.scan_workflow_step = "2 · Map & Probe"
        src = focus.get("source") or "upstream deck"
        ui.label(
            f"Inbound probe focus from {src} — axes {session.scan_cart_x_key} × {session.scan_cart_y_key}."
        ).classes("text-caption text-orange q-mb-sm")
    else:
        session.scan_workflow_step = "1 · Setup & Run"
        ui.label(
            "Inbound scan axes applied from handoff — run cartography on Setup first (Map & Probe needs a report)."
        ).classes("text-caption text-orange q-mb-sm")
    session.scan_probe_focus = None


def _refresh_all() -> None:
    _render_verdict.refresh()
    _render_workflow_chrome.refresh()
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

    art, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        pd_prerequisite_gate(
            "Run **Point Designer → Evaluate Point** first — Scan Lab uses that baseline.",
        )
        return

    _consume_scan_probe_focus(session)

    from ui_nicegui.lib.pd_solver_helpers import inputs_stale
    from ui_nicegui.lib.scan_helpers import scan_cartography_stale_vs_session
    from ui_nicegui.lib.session_store import get_cached_verdict_summary

    _vs = get_cached_verdict_summary(session, point_out)
    stale_pd = bool(getattr(session, "pd_last_run_ts", None) and inputs_stale(session))
    map_stale = scan_cartography_stale_vs_session(session)

    if stale_pd:
        ui.badge("STALE", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "Inputs changed since Point Designer evaluation — re-evaluate before trusting baseline KPIs."
        ).classes("text-caption text-orange q-mb-xs")
    if map_stale:
        ui.badge("SCAN MAP STALE", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "Cartography baseline drifted from current session inputs — re-run scan on **Setup & Run** "
            "before treating Map & Probe / Interpret as current."
        ).classes("text-caption text-orange q-mb-xs")

    caption = baseline_kpi_caption(
        point_out,
        artifact=art,
        verdict=_vs,
        design_intent=str(session.design_intent),
        fuel_mode=str((session.inputs or {}).get("fuel_mode", "DT")),
    )
    if stale_pd:
        caption = "STALE · " + caption
    kpi_cls = baseline_kpi_classes(point_out, verdict=_vs)
    if stale_pd:
        kpi_cls = "text-caption text-negative"

    with ui.row().classes("w-full items-center justify-between q-mb-sm flex-wrap"):
        ui.label(caption).classes(kpi_cls)
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.scan_teaching_mode,
                on_change=lambda e: (
                    sync_deck_guided_to_helm(session, bool(e.value), deck_attr="scan_teaching_mode"),
                    _refresh_tab_body_if_idle(session),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.scan_expert_view,
                on_change=lambda e: (
                    sync_deck_expert_to_helm(session, bool(e.value), deck_attr="scan_expert_view"),
                    _refresh_tab_body_if_idle(session),
                ),
            )

    from ui_nicegui.lib.pd_intent_policy import policy_caption

    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-xs")
    _render_verdict(session)
    _render_workflow_chrome(session)
    _render_tab_body(session)


@ui.refreshable
def _render_workflow_chrome(session: DesignSession) -> None:
    ui.select(
        DECISION_STATES,
        label="What are you trying to learn?",
        value=session.scan_decision_state
        if session.scan_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=lambda e: (
            setattr(session, "scan_decision_state", str(e.value)),
            _on_decision_scan(session, str(e.value)),
        ),
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    with ui.row().classes("w-full items-end gap-2 q-mb-xs"):
        qj = ui.input(
            "Quick jump (D/F/I/C)",
            value="",
            on_change=lambda e: _handle_quick_jump(session, str(e.value or "").strip().upper()),
        ).props("dense clearable").classes("flex-none").style("max-width: 180px")
        qj.tooltip(
            "D = Design map (cartography) · F = Feasibility interpret · "
            "I = Intent compare · C = Causality / dominance workbench"
        )
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
            _refresh_tab_body_if_idle(session),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_scan_tab(session.scan_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")


def _on_decision_scan(session: DesignSession, state: str) -> None:
    if getattr(session, "scan_running", False) or getattr(session, "scan_legacy_running", False):
        ui.notify(
            "Scan Lab job running — wait until it finishes before changing decision/Setup view.",
            type="warning",
        )
        return
    session.scan_decision_state = state
    tab = DECISION_TO_TAB.get(state)
    if tab and session.scan_teaching_mode:
        session.scan_workflow_step = tab
        # Do not re-apply stale quick-jump mode — it overwrites the decision tab.
        session.scan_view_mode = ""
        _render_workflow_chrome.refresh()
        _render_tab_body.refresh()


def _handle_quick_jump(session: DesignSession, cmd: str) -> None:
    if cmd not in QUICK_JUMP:
        return
    if getattr(session, "scan_running", False) or getattr(session, "scan_legacy_running", False):
        ui.notify(
            "Scan Lab job running — wait until it finishes before quick-jumping tabs.",
            type="warning",
        )
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
    _render_workflow_chrome.refresh()
    _render_tab_body.refresh()


def _apply_quick_jump(session: DesignSession, tab: str) -> None:
    """Legacy no-op kept for call-site compatibility; decision path must not re-apply D/F/I/C."""
    _ = (session, tab)


@ui.refreshable
def _render_verdict(session: DesignSession) -> None:
    from ui_nicegui.lib.scan_helpers import scan_cartography_stale_vs_session

    verdict.render_scan_verdict(
        session.scan_cartography_report,
        map_stale=scan_cartography_stale_vs_session(session),
    )


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
            render_goto_setup_button(
                session, attr="scan_workflow_step", on_refresh=_refresh_all
            )
            return
        workbench.render_workbench(session, rep, on_update=_render_tab_body.refresh)
    elif step == "3 · Interpret":
        rep = session.scan_cartography_report
        if not isinstance(rep, dict):
            empty_state("Run a cartography scan first.", kind="info")
            render_goto_setup_button(
                session, attr="scan_workflow_step", on_refresh=_refresh_all
            )
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
