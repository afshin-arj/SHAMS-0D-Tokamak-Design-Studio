"""Point Designer deck — NiceGUI Truth Console.

Verdict-first layout: hero → Configure | Telemetry | Constraints tabs.
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
from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context
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
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def _refresh_all() -> None:
    _render_hero.refresh()
    _refresh_tabs.refresh()


def render_point_designer(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "point")
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
                    _refresh_workflow.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.pd_expert_view,
                on_change=lambda e: setattr(session, "pd_expert_view", bool(e.value)),
            )

    _render_workflow(session)
    _render_hero(session)

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
        try:
            result = await run.io_bound(run_point_designer_evaluation, session)
            ok = bool(result.get("ok", True))
            out = result.get("outputs") or {}
            inputs_dict = result.get("inputs") or dict(session.inputs)
            set_point_evaluation(session, outputs=out, inputs=inputs_dict)
            if ok:
                ui.notify("Point evaluation complete. Open Telemetry for results.", type="positive")
                session.pd_workflow_tab = "2 · Telemetry"
            else:
                ui.notify(
                    "Solver did not fully converge — cached best-effort results. "
                    "See Run history & export for trace.",
                    type="warning",
                )
            _refresh_all()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Evaluation failed: {exc}", type="negative")
        finally:
            session.evaluating = False
            runlock_release("PointDesigner")
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status

            refresh_status()
            refresh_helm()

    _refresh_tabs(session, on_evaluate=_evaluate)


@ui.refreshable
def _render_workflow(session: DesignSession) -> None:
    def _on_decision(e) -> None:
        state = str(e.value)
        session.pd_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.pd_teaching_mode:
            session.pd_workflow_tab = tab
            _refresh_tabs.refresh()

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
            _refresh_tabs.refresh(),
        ),
    ).classes("w-full q-mb-xs")
    help_text = TAB_HELP.get(normalize_pd_tab(session.pd_workflow_tab), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")


@ui.refreshable
def _render_hero(session: DesignSession) -> None:
    from ui_nicegui.decks.point_designer.hero import render_hero

    ui.separator()
    render_hero(session)
    ui.separator()


@ui.refreshable
def _refresh_tabs(session: DesignSession, *, on_evaluate) -> None:
    tab_key = normalize_pd_tab(session.pd_workflow_tab)
    tab_index = PD_TRUTH_TABS.index(tab_key) if tab_key in PD_TRUTH_TABS else 0

    with ui.tabs().classes("w-full") as tabs:
        t_cfg = ui.tab("Configure", icon="settings")
        t_tel = ui.tab("Telemetry", icon="monitoring")
        t_con = ui.tab("Constraints", icon="rule")

    tab_refs = [t_cfg, t_tel, t_con]
    with ui.tab_panels(tabs, value=tab_refs[tab_index]).classes("w-full"):
        with ui.tab_panel(t_cfg):
            render_configure(session, on_evaluate=on_evaluate)
        with ui.tab_panel(t_tel):
            render_telemetry(session)
        with ui.tab_panel(t_con):
            render_constraints(session)


def _set_subdeck(session: DesignSession, value: str) -> None:
    session.pd_subdeck = value
