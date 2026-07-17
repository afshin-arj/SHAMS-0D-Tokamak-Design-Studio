"""Point Designer deck — NiceGUI Truth Console.

Verdict-first layout: hero → Configure | Telemetry | Constraints workflow.
Evaluate path: build_point_inputs → direct or solver → session store.
"""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.point_designer.configure import render_configure
from ui_nicegui.decks.point_designer.constraints import render_constraints
from ui_nicegui.decks.point_designer.phase_envelopes import render_phase_envelopes
from ui_nicegui.decks.point_designer.uncertainty_contracts import render_uncertainty_contracts
from ui_nicegui.decks.point_designer.telemetry import render_telemetry
from ui_nicegui.lib.pd_solver_helpers import run_point_designer_evaluation
from ui_nicegui.lib.pd_workflow_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    PD_TRUTH_TABS,
    TAB_HELP,
    normalize_pd_tab,
    teaching_banner,
)
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pd_input_guardrails import unrealistic_point_input_warnings
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def _pd_active(session: DesignSession) -> bool:
    return session.active_deck == "Point Designer"


def _refresh_all(session: DesignSession) -> None:
    if not _pd_active(session):
        return
    _render_hero.refresh()
    _render_workflow.refresh()
    _render_tab_body.refresh()


def render_point_designer(session: DesignSession) -> None:
    ui.label("Point Designer").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("point", default_open=False)

    with ui.row().classes("w-full q-mb-md"):
        ui.toggle(
            ["Truth Console", "Phase Envelopes", "Uncertainty Contracts"],
            value=session.pd_subdeck,
            on_change=lambda e: _set_subdeck(session, e.value),
        )

    if session.pd_subdeck == "Phase Envelopes":
        render_phase_envelopes(session)
        return
    if session.pd_subdeck == "Uncertainty Contracts":
        render_uncertainty_contracts(session)
        return
    if session.pd_subdeck != "Truth Console":
        empty_state(
            f"{session.pd_subdeck} is not yet ported to NiceGUI. "
            "Use Streamlit run_ui.cmd for outer-loop diagnostics.",
            kind="info",
        )
        return

    # Studio default entry (Independence 3.4): verdict-first landing card until
    # the first evaluation (or dismiss). Propose-only — user still clicks Evaluate.
    if not (session.pd_last_outputs or session.last_eval) and not session.studio_entry_dismissed:
        from ui_nicegui.components.studio_entry_panel import render_studio_entry
        from ui_nicegui.lib.navigation import refresh_active_deck

        render_studio_entry(session, on_loaded=refresh_active_deck)

    with ui.expansion("About this mode", icon="info").classes("w-full q-mb-sm"):
        ui.markdown(
            "**Point Designer is frozen** — single operating point, constraint-authoritative, "
            "no optimization. Cartography belongs in **Scan Lab**; systems closure/recovery in **Systems Mode**."
        )
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                ui.markdown(
                    "**What this mode does**\n"
                    "- Evaluates one point via `Evaluator.evaluate()` → `hot_ion_point()`\n"
                    "- Reports pass/fail margins and subsystem contracts\n"
                    "- Produces reproducible artifacts for Compare / Control Room"
                )
            with ui.column().classes("flex-1"):
                ui.markdown(
                    "**What this mode does not do**\n"
                    "- Optimize, relax, or negotiate constraints inside L0\n"
                    "- Apply designs or suggest parameter changes automatically\n"
                    "- Modify frozen physics without governance versioning"
                )

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        out = session.pd_last_outputs or session.last_eval
        if out:
            ui.label("Evaluation loaded — open Telemetry or Constraints").classes(
                "text-caption text-positive"
            )
        else:
            ui.label("No evaluation yet — Configure then Evaluate Point").classes(
                "text-caption text-grey"
            )
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.pd_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "pd_teaching_mode", bool(e.value)),
                    _render_workflow.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.pd_expert_view,
                on_change=lambda e: (
                    setattr(session, "pd_expert_view", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )

    _render_hero(session)
    _render_workflow(session)

    async def _evaluate() -> None:
        if session.evaluating:
            ui.notify("Evaluation already in progress", type="warning")
            return
        locked, task, is_owner = runlock_status("PointDesigner")
        if locked and not is_owner:
            ui.notify(f"Run lock busy: {task or 'another task'}", type="warning")
            return
        if not runlock_acquire("Point Designer: Evaluate Point", "PointDesigner"):
            ui.notify("Run lock busy (another deck is evaluating).", type="warning")
            return
        session.evaluating = True
        session.last_error = None
        mode = str(session.pd_eval_mode)
        ui.notify(f"Evaluating frozen 0-D point ({mode})…", type="info")
        log_ui_event(session, "PointDesigner", "EvaluatePoint", {"mode": mode})
        try:
            base = session.build_point_inputs()
            for warn in unrealistic_point_input_warnings(base, context="Point Designer"):
                ui.notify(warn, type="warning")
            result = await run.io_bound(run_point_designer_evaluation, session)
            ok = bool(result.get("ok", True))
            out = result.get("outputs") or {}
            inputs_dict = result.get("inputs") or dict(session.inputs)
            set_point_evaluation(session, outputs=out, inputs=inputs_dict)
            vsum = verdict_summary(out) if out else {}
            log_ui_event(
                session,
                "PointDesigner",
                "EvaluatePointResult",
                {
                    "ok": ok,
                    "mode": mode,
                    "Q_DT_eqv": out.get("Q_DT_eqv"),
                    "H98": out.get("H98"),
                    "verdict": vsum.get("verdict", "unknown"),
                    "feasible": vsum.get("feasible"),
                },
            )
            if ok:
                ui.notify("Point evaluation complete. Open Telemetry for results.", type="positive")
                session.pd_workflow_tab = "2 · Telemetry"
            else:
                msg = "Solver did not fully meet targets"
                if bool(out.get("_solver_clamped")) or bool(out.get("_solver_clamped_Q")):
                    msg += " (clamped to bounds)"
                ui.notify(
                    f"{msg} — best-effort results cached. See Chronicle for trace.",
                    type="warning",
                )
            if mode in ("solver", "envelope"):
                try:
                    ip = float(session.inputs.get("Ip_MA", 0))
                    fg = float(session.inputs.get("fG", 0))
                    ui.notify(f"Solver set Ip={ip:.4g} MA, fG={fg:.4g}", type="info")
                except (TypeError, ValueError):
                    pass
            _refresh_all(session)
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Evaluation failed: {exc}", type="negative")
        finally:
            session.evaluating = False
            runlock_release("PointDesigner")
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status

            refresh_status()
            refresh_helm()

    _render_tab_body(session, on_evaluate=_evaluate)


@ui.refreshable
def _render_workflow(session: DesignSession) -> None:
    if not _pd_active(session):
        return
    def _on_decision(e) -> None:
        state = str(e.value)
        session.pd_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.pd_teaching_mode:
            session.pd_workflow_tab = tab
            _render_workflow.refresh()
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to do?",
        value=session.pd_decision_state
        if session.pd_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.pd_workflow_tab = normalize_pd_tab(session.pd_workflow_tab)
    ui.toggle(
        PD_TRUTH_TABS,
        value=session.pd_workflow_tab,
        on_change=lambda e: (
            setattr(session, "pd_workflow_tab", normalize_pd_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full q-mb-xs")
    help_text = TAB_HELP.get(normalize_pd_tab(session.pd_workflow_tab), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")


@ui.refreshable
def _render_hero(session: DesignSession) -> None:
    if not _pd_active(session):
        return
    from ui_nicegui.decks.point_designer.hero import render_hero

    ui.separator()
    render_hero(session)
    ui.separator()


@ui.refreshable
def _render_tab_body(session: DesignSession, *, on_evaluate) -> None:
    if not _pd_active(session):
        return
    tab_key = normalize_pd_tab(session.pd_workflow_tab)

    def _goto_configure_refresh() -> None:
        _refresh_all(session)

    if tab_key == "1 · Configure":
        render_configure(session, on_evaluate=on_evaluate, on_refresh=lambda: _render_tab_body.refresh())
    elif tab_key == "2 · Telemetry":
        render_telemetry(session, on_refresh=_goto_configure_refresh)
    else:
        render_constraints(session, on_refresh=_goto_configure_refresh)


def _set_subdeck(session: DesignSession, value: str) -> None:
    session.pd_subdeck = str(value)
    from ui_nicegui.lib.navigation import refresh_active_deck

    refresh_active_deck()
