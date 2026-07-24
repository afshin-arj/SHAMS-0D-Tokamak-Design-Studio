"""Trade Study setup and run controls."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.trade_study_helpers import (
    build_study_capsule,
    default_objectives,
    objectives_catalog,
    run_studio_trade_study,
    suggested_objectives_for_knob_set,
)
from ui_nicegui.session import DesignSession

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def render_study_controls(
    session: DesignSession,
    *,
    flat: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
    on_change: Optional[Callable[[], None]] = None,
) -> None:
    knob_sets = default_knob_sets()
    names = [k.name for k in knob_sets]

    ui.label("Deterministic Trade Study").classes("text-subtitle1")
    ui.select(
        names,
        label="Knob set",
        value=session.trade_knob_set or names[0],
        on_change=lambda e: _on_knob_set(session, str(e.value), knob_sets, on_change),
    ).classes("w-full")
    ksel = next((k for k in knob_sets if k.name == (session.trade_knob_set or names[0])), knob_sets[0])
    ui.label(ksel.notes).classes("text-caption text-grey q-mb-sm")

    ui.label(f"Design intent (feasibility lens): {session.design_intent}").classes("text-caption")
    ui.label(
        "Research: only q95 blocks Pareto membership; TBR ignored; engineering limits diagnostic. "
        "Reactor: full governance hard set blocks."
    ).classes("text-caption text-grey q-mb-sm")

    obj_names, obj_senses = objectives_catalog()
    if not session.trade_objectives:
        session.trade_objectives = default_objectives()

    with ui.row().classes("w-full gap-4"):
        ui.number(
            "Budget (samples)",
            value=session.trade_n_samples,
            min=20,
            max=2000,
            step=20,
            on_change=lambda e: setattr(session, "trade_n_samples", int(e.value or 200)),
        ).classes("flex-1")
        ui.number(
            "Seed",
            value=session.trade_seed,
            step=1,
            on_change=lambda e: setattr(session, "trade_seed", int(e.value or 7)),
        ).classes("flex-1")

    ui.select(
        obj_names,
        label="Objectives (Pareto over blocking-OK points)",
        value=session.trade_objectives,
        multiple=True,
        on_change=lambda e: setattr(
            session,
            "trade_objectives",
            list(e.value) if e.value else [],
        ),
    ).classes("w-full")

    ui.button(
        "Suggest objectives for knob set",
        icon="lightbulb",
        on_click=lambda: _apply_suggested_objectives(session, names, on_change),
    ).props("flat dense")

    ui.toggle(
        ["Nominal only", "Optimistic vs Robust"],
        value=session.trade_lane_mode,
        on_change=lambda e: setattr(session, "trade_lane_mode", str(e.value)),
    ).classes("q-mb-sm")

    if len(session.trade_objectives) < 1:
        ui.label("Select at least one objective.").classes("text-orange")

    if session.trade_running:
        ui.linear_progress(show_value=False).props("indeterminate").classes("w-full q-my-sm")

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        if session.trade_running:
            ui.notify("Trade study already running", type="warning")
            return
        if not session.trade_objectives:
            ui.notify("Select at least one objective", type="warning")
            return
        locked, task, is_owner = runlock_status("TradeStudy")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Trade Study Studio", "TradeStudy"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        ksel_now = next(
            (k for k in knob_sets if k.name == (session.trade_knob_set or names[0])),
            knob_sets[0],
        )
        _, catalog_senses = objectives_catalog()
        senses = {o: str(catalog_senses.get(o, "min")) for o in session.trade_objectives}
        session.trade_running = True
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_status()
        refresh_helm()
        ui.notify("Running trade study…", type="info")
        try:
            base = session.build_point_inputs()
            rep = await run.io_bound(
                run_studio_trade_study,
                base,
                knob_set=ksel_now,
                objectives=list(session.trade_objectives),
                objective_senses=senses,
                n_samples=session.trade_n_samples,
                seed=session.trade_seed,
                design_intent=session.design_intent,
            )
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.trade_last = rep
            session.trade_last_lane = session.trade_lane_mode
            session.active_study_capsule = build_study_capsule(
                rep, base, ksel_now, lane_mode=session.trade_lane_mode
            )
            summary = rep.get("summary") or {}
            ui.notify(
                f"Done: {summary.get('n_feasible', 0)} blocking-OK, "
                f"{summary.get('n_pareto', 0)} Pareto points (screening — not L0 FEASIBLE)",
                type="info",
            )
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Trade study failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                session.trade_running = False
                runlock_release("TradeStudy", lease)
                # Remount after clearing busy so Run re-enables (not stuck disabled mid-flag).
                if on_complete:
                    on_complete()

    btn = ui.button("Run trade study (blocking-OK only)", icon="play_arrow", on_click=_run).props("color=primary")
    if session.trade_running or not session.trade_objectives:
        btn.props("disable")


def _apply_suggested_objectives(
    session: DesignSession,
    knob_names: list[str],
    on_change: Optional[Callable[[], None]] = None,
) -> None:
    session.trade_objectives = suggested_objectives_for_knob_set(
        session.trade_knob_set or (knob_names[0] if knob_names else "")
    )
    if on_change:
        on_change()


def _on_knob_set(
    session: DesignSession,
    name: str,
    knob_sets,
    on_change: Optional[Callable[[], None]] = None,
) -> None:
    session.trade_knob_set = name
    if not session.trade_objectives:
        session.trade_objectives = suggested_objectives_for_knob_set(name)
    if on_change:
        on_change()
