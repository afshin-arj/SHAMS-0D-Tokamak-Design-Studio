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
from ui_nicegui.lib.deck_busy_guard import FORGE_RUNNING_ATTRS, refresh_tab_if_idle
from ui_nicegui.lib.forge_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    FORGE_TABS,
    TAB_HELP,
    next_action_hint,
    normalize_forge_tab,
    teaching_banner,
)
from ui_nicegui.lib.forge_helpers import summarize_forge_state
from ui_nicegui.lib.forge_machine_finder_helpers import summarize_workbench_run
from ui_nicegui.session import DesignSession
from ui_nicegui.lib.expert_mode import sync_deck_expert_to_helm
from ui_nicegui.lib.teaching_mode import sync_deck_guided_to_helm

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
    if any(bool(getattr(session, a, False)) for a in FORGE_RUNNING_ATTRS):
        ui.notify(
            "Reactor Design Forge running — wait until it finishes before toggling Review Mode.",
            type="warning",
        )
        return
    session.forge_review_mode = bool(value)
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()
    _render_tab_body.refresh()


def _sync_legacy_deck(session: DesignSession, tab: str) -> None:
    session.forge_deck = _LEGACY_FROM_TAB.get(tab, "Intent Compiler")


def _on_forge_tab_change(session: DesignSession, raw: str) -> None:
    """Advance workflow tab only when no Forge long-job is live (avoid chrome/body desync)."""
    if any(bool(getattr(session, a, False)) for a in FORGE_RUNNING_ATTRS):
        ui.notify(
            "Reactor Design Forge running — wait until it finishes before changing Guided / Expert / tabs.",
            type="warning",
        )
        return
    tab = normalize_forge_tab(raw)
    session.forge_workflow_step = tab
    _sync_legacy_deck(session, tab)
    _render_tab_body.refresh()


def _has_forge_workbench(session: DesignSession) -> bool:
    run = getattr(session, "forge_workbench_run", None)
    return isinstance(run, dict) and run.get("archive") is not None


def _render_busy_strip(session: DesignSession) -> None:
    """Deck-level busy chrome — remount-safe when returning mid-job (NAV-IMMEDIATE)."""
    busy = [a for a in FORGE_RUNNING_ATTRS if getattr(session, a, False)]
    if not busy:
        return
    with ui.card().classes("w-full p-2 bg-blue-1 text-blue-10 q-mb-sm"):
        ui.label(f"Forge busy — {', '.join(busy)}").classes("text-subtitle2")
        ui.label(
            "Helm deck switch stays immediate (NAV-IMMEDIATE-001). "
            "Guided / Expert / tab remounts are blocked until the job finishes."
        ).classes("text-caption")


def render_reactor_design_forge(session: DesignSession) -> None:
    ui.label("Reactor Design Forge").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("forge", default_open=False)
    _render_busy_strip(session)

    art, _, point_out = get_point_artifact_triple(session)
    has_wb = _has_forge_workbench(session)
    # Promote/Apply clears PD eval — do not hide a live Machine Finder archive behind the gate.
    if not isinstance(point_out, dict) and not has_wb:
        pd_prerequisite_gate(
            "Run **Point Designer → Evaluate Point** first — Forge uses that baseline.",
        )
        return
    if not isinstance(point_out, dict) and has_wb:
        ui.badge("BASELINE CLEARED", color="orange").props("outline").classes("q-mb-xs")
        ui.label(
            "Point Designer evaluation was cleared (promote/Apply). "
            "Workbench archive is still available — open Point Designer and **Evaluate Point** "
            "to restore the baseline KPI strip, or continue Instruments / Capsules."
        ).classes("text-caption text-orange q-mb-sm")
        # Soft gate: still allow workflow chrome + tabs without KPI hero.
        from ui_nicegui.lib.pd_intent_policy import policy_caption

        ui.label(policy_caption(session.design_intent)).classes("text-caption q-mb-xs")
        with ui.card().classes("w-full q-mb-sm q-pa-sm bg-blue-grey-1"):
            ui.markdown(f"**Do now:** {next_action_hint(session)}").classes("text-body2")
        if session.forge_review_mode:
            ui.label("Review Mode: search/compile controls locked; inspect archives and export only.").classes(
                "text-orange q-mb-sm"
            )
        _render_dashboard(session)
        session.forge_workflow_step = normalize_forge_tab(session.forge_workflow_step)
        _sync_legacy_deck(session, session.forge_workflow_step)
        ui.toggle(
            FORGE_TABS,
            value=session.forge_workflow_step,
            on_change=lambda e: _on_forge_tab_change(session, str(e.value)),
        ).classes("w-full")
        _render_tab_body(session)
        return

    from ui_nicegui.lib.session_store import get_cached_verdict_summary

    _vs = get_cached_verdict_summary(session, point_out)
    fuel = str((session.inputs or {}).get("fuel_mode", "DT"))
    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        ui.label(
            baseline_kpi_caption(
                point_out,
                artifact=art,
                verdict=_vs,
                design_intent=str(session.design_intent),
                fuel_mode=fuel,
            )
        ).classes(baseline_kpi_classes(point_out, verdict=_vs))
        with ui.row().classes("gap-4 flex-wrap"):
            ui.switch(
                "Guided mode",
                value=session.forge_teaching_mode,
                on_change=lambda e: (
                    sync_deck_guided_to_helm(session, bool(e.value), deck_attr="forge_teaching_mode"),
                    refresh_tab_if_idle(
                        session,
                        running_attrs=FORGE_RUNNING_ATTRS,
                        refresh=_render_tab_body.refresh,
                        job_label="Reactor Design Forge",
                    ),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.forge_expert_view,
                on_change=lambda e: (
                    sync_deck_expert_to_helm(session, bool(e.value), deck_attr="forge_expert_view"),
                    refresh_tab_if_idle(
                        session,
                        running_attrs=FORGE_RUNNING_ATTRS,
                        refresh=_render_tab_body.refresh,
                        job_label="Reactor Design Forge",
                    ),
                ),
            )
            ui.switch(
                "Review Mode (locks run controls)",
                value=session.forge_review_mode,
                on_change=lambda e: _set_forge_review_mode(session, bool(e.value)),
            )

    from ui_nicegui.lib.pd_intent_policy import policy_caption

    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-xs")
    with ui.card().classes("w-full q-mb-sm q-pa-sm bg-blue-grey-1"):
        ui.markdown(f"**Do now:** {next_action_hint(session)}").classes("text-body2")

    if session.forge_review_mode:
        ui.label("Review Mode: search/compile controls locked; inspect archives and export only.").classes(
            "text-orange q-mb-sm"
        )

    _render_dashboard(session)
    def _on_decision(e) -> None:
        if any(bool(getattr(session, a, False)) for a in FORGE_RUNNING_ATTRS):
            ui.notify(
                "Forge job running — wait until it finishes before changing decision/Setup view.",
                type="warning",
            )
            return
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
        on_change=lambda e: _on_forge_tab_change(session, str(e.value)),
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
        n_ok = wb.get("n_feasible_archive")
        n_all = wb.get("n_archive")
        prior_l0 = summary.get("audit_feasible")
        summary = {
            **{k: v for k, v in summary.items() if k != "audit_feasible"},
            "loaded": True,
            "workbench_loaded": True,
            "screening_posture": "ARCHIVE SCREENING",
            "n_feasible_archive": n_ok,
            "n_archive": n_all,
            "audit_verdict": (
                f"Archive blocking-OK {n_ok}/{n_all} (screening — not L0 hero)"
            ),
            "dominant": wb.get("top_blocker") or wb.get("dominant_resistance") or summary.get("dominant"),
            "l0_audit_feasible": prior_l0,
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
