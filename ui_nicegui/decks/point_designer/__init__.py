"""Point Designer deck — NiceGUI Truth Console (Phase 20 complete).



Verdict-first layout: hero → Configure | Telemetry | Constraints tabs.

Evaluate path: build_point_inputs → direct or solver → session store.

"""

from __future__ import annotations



from nicegui import run, ui



from ui_nicegui.components.empty_state import empty_state

from ui_nicegui.decks.point_designer.configure import render_configure

from ui_nicegui.decks.point_designer.constraints import render_constraints

from ui_nicegui.decks.point_designer.hero import render_hero

from ui_nicegui.decks.point_designer.phase_envelopes import render_phase_envelopes

from ui_nicegui.decks.point_designer.uncertainty_contracts import render_uncertainty_contracts

from ui_nicegui.decks.point_designer.telemetry import render_telemetry

from ui_nicegui.lib.pd_solver_helpers import run_point_designer_evaluation
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.lib.session_store import set_point_evaluation

from ui_nicegui.session import DesignSession





def render_point_designer(session: DesignSession) -> None:

    ui.label("Point Designer").classes("text-h5")

    ui.label("Frozen 0-D truth console — panels propose, evaluator decides.").classes(

        "text-caption text-grey q-mb-sm"

    )



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



    with ui.expansion("About this mode", icon="info").classes("w-full q-mb-sm"):

        ui.markdown(

            "**Point Designer is frozen** — single operating point, constraint-authoritative, "

            "no optimization. Exploration belongs in **Systems Mode**."

        )



    render_hero(session)

    ui.separator()



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
            else:
                ui.notify(
                    "Solver did not fully converge — cached best-effort results. "
                    "See Run history & export for trace.",
                    type="warning",
                )
            _refresh_tabs.refresh()
            render_hero(session)
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

def _refresh_tabs(session: DesignSession, *, on_evaluate) -> None:

    with ui.tabs().classes("w-full") as tabs:

        t_cfg = ui.tab("Configure", icon="settings")

        t_tel = ui.tab("Telemetry", icon="monitoring")

        t_con = ui.tab("Constraints", icon="rule")

    with ui.tab_panels(tabs, value=t_cfg).classes("w-full"):

        with ui.tab_panel(t_cfg):

            render_configure(session, on_evaluate=on_evaluate)

        with ui.tab_panel(t_tel):

            render_telemetry(session)

        with ui.tab_panel(t_con):

            render_constraints(session)





def _set_subdeck(session: DesignSession, value: str) -> None:

    session.pd_subdeck = value


