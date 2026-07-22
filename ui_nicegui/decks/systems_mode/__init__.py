"""Systems Mode deck — workflow-ordered UX + full Streamlit parity."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.systems_mode import (
    apply_ui,
    assistant_ui,
    atlas_ui,
    audit_ui,
    base_design_ui,
    certification_ui,
    chronicle_ui,
    diagnostics_ui,
    explore_ui,
    export_ui,
    frontier_ui,
    precheck_ui,
    recover_ui,
    reproduce_ui,
    setup,
    solve_ui,
    stories_ui,
    timeline_ui,
    tools_ui,
    verdict,
)
from ui_nicegui.lib.pd_intent_policy import policy_caption
from ui_nicegui.lib.systems_artifact import fetch_systems_artifact
from ui_nicegui.lib.expert_mode import sync_deck_expert_to_helm
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pd_input_guardrails import unrealistic_point_input_warnings
from ui_nicegui.lib.systems_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    SYSTEMS_TABS,
    TAB_HELP,
    next_action_hint,
    normalize_systems_tab,
    teaching_banner,
)
from ui_nicegui.lib.systems_handoff import consume_systems_mode_queue
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.lib.systems_workflow_helpers import collect_candidates
from ui_nicegui.session import DesignSession
from ui_nicegui.lib.teaching_mode import sync_deck_guided_to_helm


def _precheck_ok(session: DesignSession) -> bool | None:
    report = session.last_precheck_report
    if report is None:
        return None
    try:
        return bool(getattr(report, "ok", report.get("ok") if isinstance(report, dict) else False))
    except Exception:
        return None


def _solve_ok(session: DesignSession) -> bool | None:
    result = session.systems_last_solve_result
    if not isinstance(result, dict):
        return None
    return bool(result.get("ok"))


def _artifact_source(art: dict | None) -> str | None:
    if not isinstance(art, dict):
        return None
    return str(art.get("source") or "")


def render_systems_mode(session: DesignSession) -> None:
    consume_systems_mode_queue(session)
    session.systems_workflow_step = normalize_systems_tab(session.systems_workflow_step)

    if session.pd_pending_systems_action == "precheck":
        session.pd_pending_systems_action = None
        session.systems_workflow_step = "2 · Check & Solve"
        ui.notify("Point Designer handoff — run Step ① precheck on this tab.", type="info")

    with ui.row().classes("w-full items-center justify-between"):
        ui.label("Systems Mode").classes("text-h5")
        ui.switch(
            "Expert view",
            value=session.systems_expert_view,
            on_change=lambda e: (
                sync_deck_expert_to_helm(session, bool(e.value), deck_attr="systems_expert_view"),
                _render_tab_content.refresh(),
            ),
        )

    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-xs")
    ui.markdown(
        "**Systems Mode** — Monte Carlo precheck + Newton solve (proposes inputs; never changes L0). "
        "This is **not System Suite** (read-only L1 overlays on a Point Designer artifact)."
    ).classes("text-caption q-mb-xs")
    from ui_nicegui.components.certified_opt_honesty_banner import (
        render_certified_opt_honesty_banner,
    )

    render_certified_opt_honesty_banner("systems_mode")
    from ui_nicegui.components.opt_lab_warm_start_panel import render_champion_warm_start

    with ui.expansion("Champion warm-start (search seed)", icon="bolt", value=False).classes(
        "w-full q-mb-sm"
    ):
        render_champion_warm_start(session, compact=True)
    render_mode_scope("systems_eval", default_open=False)
    ui.label(policy_caption(session.design_intent)).classes("text-caption q-mb-sm")

    from ui_nicegui.lib.artifact_access import get_point_artifact_triple

    _art, _, _point_out = get_point_artifact_triple(session)
    if not isinstance(_point_out, dict):
        ui.label(
            "No Point Designer evaluation loaded — solve still runs against machine defaults "
            "(propose-only). Evaluate a baseline in Point Designer for a grounded seed."
        ).classes("text-caption text-orange q-mb-sm")

    def _on_decision(e) -> None:
        state = str(e.value)
        session.systems_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.systems_teaching_mode:
            session.systems_workflow_step = tab
            _render_posture.refresh()
            _render_workflow_chips.refresh()
            _render_tab_content.refresh()

    with ui.row().classes("w-full gap-4 flex-wrap items-center q-mb-sm"):
        ui.select(
            DECISION_STATES,
            label="What are you trying to do?",
            value=session.systems_decision_state
            if session.systems_decision_state in DECISION_STATES
            else DECISION_STATES[0],
            on_change=_on_decision,
        ).classes("flex-[2]")
        ui.switch(
            "Guided mode",
            value=session.systems_teaching_mode,
            on_change=lambda e: (
                sync_deck_guided_to_helm(session, bool(e.value), deck_attr="systems_teaching_mode"),
                _render_posture.refresh(),
            ),
        )
    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    _render_posture(session)
    _render_workflow_chips(session)
    _render_workflow_tabs(session)
    _render_tab_content(session)


@ui.refreshable
def _render_workflow_tabs(session: DesignSession) -> None:
    step = normalize_systems_tab(session.systems_workflow_step)
    ui.toggle(
        SYSTEMS_TABS,
        value=step,
        on_change=lambda e: (
            setattr(session, "systems_workflow_step", normalize_systems_tab(str(e.value))),
            _render_tab_content.refresh(),
        ),
    ).classes("w-full q-mb-xs")
    ui.label(TAB_HELP.get(step, "")).classes("text-caption text-grey q-mb-md")


@ui.refreshable
def _render_posture(session: DesignSession) -> None:
    art = fetch_systems_artifact(session)
    _, targets, variables = resolve_systems_problem(session)
    targets_ok = bool(targets and variables)
    n_cands = len(collect_candidates(session))
    has_art = isinstance(art, dict)

    hint = next_action_hint(
        has_artifact=has_art,
        artifact_source=_artifact_source(art),
        targets_ok=targets_ok,
        precheck_ok=_precheck_ok(session),
        solve_ok=_solve_ok(session),
        n_candidates=n_cands,
    )

    if has_art:
        fuel = str((session.inputs or {}).get("fuel_mode", "DT"))
        try:
            from ui_nicegui.lib.pd_solver_helpers import inputs_stale

            if inputs_stale(session):
                ui.badge("STALE", color="orange").props("outline").classes("q-mb-xs")
                ui.label(
                    "Inputs changed since the last Point Designer evaluation — KPIs may not match current targets."
                ).classes("text-caption text-orange q-mb-xs")
        except Exception:
            pass
        verdict.render_posture_strip(
            art,
            next_action=hint,
            design_intent=str(session.design_intent),
            fuel_mode=fuel,
        )
        src = _artifact_source(art)
        if src == "point_designer_fallback":
            ui.label("Baseline from Point Designer — no target solve yet.").classes("text-caption text-orange")
        elif src == "point_designer_apply":
            ui.label(
                "Last artifact: Point Designer Apply re-eval — not a Systems target solve."
            ).classes("text-caption text-orange")
        elif src == "systems_recovery":
            ui.label("Last artifact: Systems recovery seed.").classes("text-caption text-blue-8")
        elif src == "systems_solve":
            ui.label("Last artifact: target solve.").classes("text-caption text-positive")
    else:
        verdict.render_degraded_posture(next_action=hint)


@ui.refreshable
def _render_workflow_chips(session: DesignSession) -> None:
    _, targets, variables = resolve_systems_problem(session)
    pre = _precheck_ok(session)
    sol = _solve_ok(session)
    n = len(collect_candidates(session))

    def _chip(label: str, state: str) -> None:
        color = {"ok": "text-positive", "fail": "text-negative", "pending": "text-grey"}.get(state, "")
        ui.label(f"{label}: {'✓' if state == 'ok' else '✗' if state == 'fail' else '—'}").classes(
            f"text-caption {color} q-mr-md"
        )

    with ui.row().classes("q-mb-sm flex-wrap"):
        _chip("Baseline", "ok" if fetch_systems_artifact(session) else "pending")
        _chip("Targets", "ok" if targets and variables else "fail")
        _chip("Precheck", "ok" if pre else ("fail" if pre is False else "pending"))
        _chip("Solve", "ok" if sol else ("fail" if sol is False else "pending"))
        ui.label(f"Candidates: {n}").classes("text-caption q-mr-md")


@ui.refreshable
def _render_tab_content(session: DesignSession) -> None:
    refresh = lambda: (
        _render_posture.refresh(),
        _render_workflow_chips.refresh(),
        _render_tab_content.refresh(),
    )
    step = normalize_systems_tab(session.systems_workflow_step)
    art = fetch_systems_artifact(session)

    if step == "1 · Targets":
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-[2]"):
                setup.render_setup(session)
            with ui.column().classes("flex-1"):
                base_design_ui.render_base_design_editor(session)
        return

    if step == "2 · Check & Solve":
        precheck_ui.render_precheck_panel(session, on_precheck_complete=refresh)
        assistant_ui.render_assistant_panel(session, on_change=refresh)
        ui.separator().classes("q-my-md")
        solve_ui.render_solve_panel(session, on_complete=refresh)
        if session.systems_expert_view:
            atlas_ui.render_atlas_panel(session)
        return

    if step == "3 · Alternatives":
        ui.label("When precheck or target solve fails, search for feasible alternatives.").classes(
            "text-caption q-mb-md"
        )
        ui.label("A · Nearest feasible point").classes("text-subtitle2")
        recover_ui.render_recover_panel(session, on_complete=refresh)
        ui.separator().classes("q-my-md")
        ui.label("B · Budgeted feasible search").classes("text-subtitle2")
        explore_ui.render_explore_panel(session, on_complete=refresh)
        frontier_ui.render_frontier_panel(session)
        if session.systems_expert_view:
            timeline_ui.render_timeline_panel(session)
        return

    if step == "4 · Apply":
        apply_ui.render_apply_panel(session, on_complete=refresh)
        return

    if step == "5 · Review":
        if isinstance(art, dict):
            with ui.expansion("Verdict & constraints", icon="gavel", value=True).classes("w-full"):
                verdict.render_causal_chain(art, inline=True, expert=session.systems_expert_view)
                verdict.render_constraint_table(art, design_intent=session.design_intent)
                verdict.render_constraint_cards(
                    art, design_intent=session.design_intent, expert=session.systems_expert_view
                )
            with ui.expansion("Diagnostics & authority", icon="science").classes("w-full q-mt-sm"):
                diagnostics_ui.render_post_solve_diagnostics_sync(session)
                if session.systems_expert_view:
                    certification_ui.render_certification_panels(session)
            with ui.expansion("Audit & export", icon="folder").classes("w-full q-mt-sm"):
                audit_ui.render_audit_panel(session)
                export_ui.render_export_panel(session)
            if session.systems_expert_view:
                with ui.expansion("Forensics & stories", icon="history").classes("w-full q-mt-sm"):
                    stories_ui.render_design_stories(session, on_change=refresh)
                    chronicle_ui.render_chronicle_panel(session)
                    reproduce_ui.render_reproduce_panel(session, on_change=refresh)
                    tools_ui.render_tools_panel(session)
        else:
            from ui_nicegui.components.empty_state import empty_state

            empty_state(
                "Run precheck/solve or apply a candidate to populate review artifacts.",
                kind="info",
            )

            def _goto_targets() -> None:
                session.systems_workflow_step = "1 · Targets"
                refresh()

            def _goto_solve() -> None:
                session.systems_workflow_step = "2 · Check & Solve"
                refresh()

            with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
                ui.button("Set targets", icon="flag", on_click=_goto_targets).props("outline")
                ui.button("Run precheck / solve", icon="play_arrow", on_click=_goto_solve).props(
                    "outline color=primary"
                )
        return
