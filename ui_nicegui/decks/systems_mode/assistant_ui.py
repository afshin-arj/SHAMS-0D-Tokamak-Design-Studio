"""Feasibility completion assistant — visible when precheck fails."""

from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.systems_assistant_helpers import propose_feasibility_changes
from ui_nicegui.lib.systems_precheck import run_systems_precheck
from ui_nicegui.lib.systems_state_helpers import (
    apply_proposal_to_session,
    pop_assistant_undo,
    push_assistant_undo,
    resolve_systems_problem,
)
from ui_nicegui.session import DesignSession


def _precheck_ok(report) -> bool:
    if report is None:
        return False
    try:
        return bool(getattr(report, "ok", report.get("ok") if isinstance(report, dict) else False))
    except Exception:
        return False


def render_assistant_panel(
    session: DesignSession,
    *,
    on_change: Optional[Callable[[], None]] = None,
) -> None:
    report = session.last_precheck_report
    if report is None or _precheck_ok(report):
        return

    with ui.card().classes("w-full q-my-sm p-3"):
        ui.label("Suggested fixes").classes("text-subtitle2")
        ui.label("Deterministic minimal bound/target changes — apply one, then re-run precheck.").classes(
            "text-caption q-mb-sm"
        )

        async def _load_proposals() -> None:
            props = await run.io_bound(
                propose_feasibility_changes,
                session,
                n_random=session.systems_precheck_n_random,
                seed=session.systems_precheck_seed,
            )
            session.systems_assistant_proposals = props
            _proposal_list.refresh()

        async def _undo() -> None:
            if pop_assistant_undo(session):
                ui.notify("Undo applied", type="info")
                if on_change:
                    on_change()
            else:
                ui.notify("Nothing to undo", type="warning")

        with ui.row().classes("gap-2 q-mb-sm"):
            ui.button("Generate proposals", icon="lightbulb", on_click=_load_proposals).props("outline")
            ui.button("Undo last", icon="undo", on_click=_undo).props("flat")

        _proposal_list(session, on_change=on_change)


@ui.refreshable
def _proposal_list(session: DesignSession, *, on_change=None) -> None:
    props = getattr(session, "systems_assistant_proposals", None) or []
    if not props:
        ui.markdown("Click **Generate proposals**.").classes("text-grey")
        return

    _, targets, variables = resolve_systems_problem(session)

    for i, pr in enumerate(props, start=1):
        with ui.row().classes("w-full items-center gap-2"):
            ui.markdown(f"**{i}.** {pr.get('description', '-')} _(score {float(pr.get('score', 0)):.3g})_").classes(
                "flex-grow"
            )

            async def _apply(p=pr) -> None:
                push_assistant_undo(session, targets=targets, variables=variables)
                apply_proposal_to_session(session, p)
                base, t_now, v_now = resolve_systems_problem(session)
                report = await run.io_bound(
                    run_systems_precheck,
                    base,
                    t_now,
                    v_now,
                    n_random=session.systems_precheck_n_random,
                    seed=session.systems_precheck_seed,
                    design_intent=session.design_intent,
                )
                session.last_precheck_report = report
                ui.notify("Applied — precheck re-run", type="positive")
                if on_change:
                    on_change()

            ui.button("Apply", on_click=_apply).props("dense outline")
