"""Pareto Lab study controls."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.pareto_helpers import (
    OBJ_CATALOG,
    OBJ_TEMPLATES,
    default_bounds,
    default_objective_sense,
    ensure_pareto_bounds,
    frontier_posture,
    metric_label,
    run_pareto_study,
    sanitize_sampling_bounds,
)
from ui_nicegui.lib.pareto_interpret_helpers import possible_next_questions
from ui_nicegui.lib.pareto_labels import ROBUST_MARGIN_HELP
from ui_nicegui.session import DesignSession


def render_pareto_controls(
    session: DesignSession,
    *,
    flat: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    base = session.build_point_inputs()
    bounds_def = default_bounds(base)
    # PARETO-BOUNDS-001: re-seed / expand stale or inverted boxes around PD baseline.
    b = ensure_pareto_bounds(session, base)

    bounds_ctx = ui.column().classes("w-full") if flat else ui.expansion(
        "Bounds (sampling hyper-rectangle)", icon="crop", value=flat
    ).classes("w-full")
    with bounds_ctx:
        with ui.row().classes("w-full gap-2"):
            ui.number("R0 min [m]", value=b["R0_m"][0], step=0.01, on_change=lambda e: _set_bound(session, "R0_m", 0, e.value)).classes("flex-1")
            ui.number("R0 max [m]", value=b["R0_m"][1], step=0.01, on_change=lambda e: _set_bound(session, "R0_m", 1, e.value)).classes("flex-1")
            ui.number("Bt min [T]", value=b["Bt_T"][0], step=0.1, on_change=lambda e: _set_bound(session, "Bt_T", 0, e.value)).classes("flex-1")
            ui.number("Bt max [T]", value=b["Bt_T"][1], step=0.1, on_change=lambda e: _set_bound(session, "Bt_T", 1, e.value)).classes("flex-1")
        with ui.row().classes("w-full gap-2 q-mt-sm"):
            ui.number("Ip min [MA]", value=b["Ip_MA"][0], step=0.1, on_change=lambda e: _set_bound(session, "Ip_MA", 0, e.value)).classes("flex-1")
            ui.number("Ip max [MA]", value=b["Ip_MA"][1], step=0.1, on_change=lambda e: _set_bound(session, "Ip_MA", 1, e.value)).classes("flex-1")
            ui.number("fG min [-]", value=b["fG"][0], step=0.05, on_change=lambda e: _set_bound(session, "fG", 0, e.value)).classes("flex-1")
            ui.number("fG max [-]", value=b["fG"][1], step=0.05, on_change=lambda e: _set_bound(session, "fG", 1, e.value)).classes("flex-1")
        if "Paux_MW" in b:
            with ui.row().classes("w-full gap-2 q-mt-sm"):
                ui.number("Paux min [MW]", value=b["Paux_MW"][0], step=1.0, on_change=lambda e: _set_bound(session, "Paux_MW", 0, e.value)).classes("flex-1")
                ui.number("Paux max [MW]", value=b["Paux_MW"][1], step=1.0, on_change=lambda e: _set_bound(session, "Paux_MW", 1, e.value)).classes("flex-1")
            ui.label("Vary Paux when Q or net-electric objectives are active.").classes("text-caption text-grey")

    obj_ctx = ui.column().classes("w-full q-mt-sm") if flat else ui.expansion(
        "Objective contract", icon="rule", value=True
    ).classes("w-full q-mt-sm")
    with obj_ctx:
        ui.select(
            list(OBJ_TEMPLATES.keys()),
            label="Objective template",
            value=session.pareto_template,
            on_change=lambda e: _apply_template(session, str(e.value)),
        ).classes("w-full")
        ui.toggle(
            ["Reactor", "Research", "Both (overlay)"],
            value=session.pareto_intent_mode,
            on_change=lambda e: setattr(session, "pareto_intent_mode", str(e.value)),
        ).classes("q-mb-sm")
        obj_keys = list(OBJ_CATALOG.keys())
        ui.select(
            obj_keys,
            label="Objectives (pick ≥2)",
            value=session.pareto_sel_objs,
            multiple=True,
            on_change=lambda e: _set_objectives(session, list(e.value) if e.value else []),
        ).classes("w-full")
        _render_objective_senses(session)
        with ui.row().classes("w-full gap-4"):
            ui.number(
                "Margin-robust threshold",
                value=session.pareto_robust_margin_thr,
                min=0.0,
                step=0.05,
                on_change=lambda e: setattr(session, "pareto_robust_margin_thr", float(e.value or 0.1)),
            ).classes("flex-1").tooltip("Min constraint margin filter for robust overlay — not UQ")
            ui.number(
                "Samples",
                value=session.pareto_n_samples,
                min=50,
                max=4000,
                step=50,
                on_change=lambda e: setattr(session, "pareto_n_samples", int(e.value or 300)),
            ).classes("flex-1")
            ui.number(
                "Seed",
                value=session.pareto_seed,
                step=1,
                on_change=lambda e: setattr(session, "pareto_seed", int(e.value or 1)),
            ).classes("flex-1")
        if len(session.pareto_sel_objs) < 2:
            ui.label("Select at least 2 objectives for a meaningful Pareto front.").classes("text-orange")
        ui.markdown(ROBUST_MARGIN_HELP).classes("text-caption text-grey q-mt-xs")

    if session.pareto_running:
        ui.linear_progress(show_value=False).props("indeterminate").classes("w-full q-my-sm")

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        if session.pareto_running:
            ui.notify("Pareto study already running", type="warning")
            return
        objectives = _objectives_dict(session)
        if len(objectives) < 2:
            ui.notify("Select at least 2 objectives", type="warning")
            return
        locked, task, is_owner = runlock_status("ParetoLab")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Pareto Lab: Study", "ParetoLab"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        from ui_nicegui.lib.run_lock import current_lease, lease_valid

        lease = current_lease()
        bounds = _resolved_bounds(session, bounds_def)
        session.pareto_running = True
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_status()
        refresh_helm()
        ui.notify("Running Pareto study (LHS sampling)…", type="info")
        try:
            result = await run.io_bound(
                run_pareto_study,
                session.build_point_inputs(),
                bounds=bounds,
                objectives=objectives,
                n_samples=session.pareto_n_samples,
                seed=session.pareto_seed,
                intent_mode=session.pareto_intent_mode,
                robust_margin_thr=session.pareto_robust_margin_thr,
                Paux_for_Q_MW=getattr(session, "paux_for_q", None),
            )
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding Pareto results.", type="warning")
                return
            session.pareto_last = result
            summary = result.get("summary") or {}
            ui.notify(
                f"Done: {summary.get('n_feasible', 0)} feasible, "
                f"{summary.get('n_pareto', 0)} Pareto points",
                type="positive",
            )
            _post_run_verdict.refresh()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Pareto study failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                session.pareto_running = False
                runlock_release("ParetoLab", lease)
                if on_complete:
                    on_complete()

    btn = ui.button("Run Pareto (feasible-only)", icon="play_arrow", on_click=_run).props("color=primary")
    if session.pareto_running or len(session.pareto_sel_objs) < 2:
        btn.props("disable")
    _post_run_verdict(session)


@ui.refreshable
def _post_run_verdict(session: DesignSession) -> None:
    rep = session.pareto_last
    if not isinstance(rep, dict):
        return
    summary = rep.get("summary") or {}
    if not summary:
        return
    posture, _ = frontier_posture(summary)
    ui.separator().classes("q-my-sm")
    ui.label("Last run verdict").classes("text-subtitle2")
    ui.label(posture).classes("text-body2")
    for q in possible_next_questions({"summary": summary, "intent_mode": rep.get("intent_mode")}):
        ui.label(f"→ {q}").classes("text-caption text-grey")
    why = rep.get("summary", {})
    ui.markdown(
        f"Feasible {why.get('n_feasible', '-')} · Pareto {why.get('n_pareto', '-')} · "
        f"Top limiter: {why.get('top_constraint', '-')} — open **Explore Frontier** to plot."
    ).classes("text-caption text-grey")


def _resolved_bounds(session: DesignSession, defaults: dict) -> dict:
    base = session.build_point_inputs()
    b = ensure_pareto_bounds(session, base)
    for k, v in defaults.items():
        if k not in b:
            b[k] = v
    return {k: (float(v[0]), float(v[1])) for k, v in b.items()}


def _set_bound(session: DesignSession, key: str, idx: int, value) -> None:
    base = session.build_point_inputs()
    if session.pareto_bounds is None:
        session.pareto_bounds = default_bounds(base)
    lo, hi = session.pareto_bounds.get(key, (0.0, 1.0))
    pair = [float(lo), float(hi)]
    try:
        pair[idx] = float(value)
    except (TypeError, ValueError):
        return
    session.pareto_bounds[key] = (pair[0], pair[1])
    # Keep lo ≤ hi after manual edits (swap edges; do not expand beyond user intent).
    session.pareto_bounds = sanitize_sampling_bounds(
        session.pareto_bounds,
        baseline=None,
        defaults=None,
    )


def _set_objectives(session: DesignSession, keys: list[str]) -> None:
    session.pareto_sel_objs = keys
    senses = dict(session.pareto_obj_senses)
    for k in keys:
        senses.setdefault(k, default_objective_sense(k))
    session.pareto_obj_senses = senses


def _apply_template(session: DesignSession, template: str) -> None:
    session.pareto_template = template
    spec = OBJ_TEMPLATES.get(template)
    if spec:
        session.pareto_sel_objs = list(spec.keys())
        session.pareto_obj_senses = dict(spec)


def _objectives_dict(session: DesignSession) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in session.pareto_sel_objs:
        out[k] = str(session.pareto_obj_senses.get(k, default_objective_sense(k)))
    return out


def _render_objective_senses(session: DesignSession) -> None:
    if len(session.pareto_sel_objs) < 1:
        return
    ui.label("Min / max sense per objective").classes("text-caption q-mt-xs")
    with ui.row().classes("w-full gap-2 flex-wrap"):
        for k in session.pareto_sel_objs:
            sense = session.pareto_obj_senses.get(k, default_objective_sense(k))
            with ui.column().classes("flex-none"):
                ui.toggle(
                    ["min", "max"],
                    value=sense,
                    on_change=lambda e, key=k: _set_sense(session, key, str(e.value)),
                ).props("dense").tooltip(metric_label(k))
                ui.label(OBJ_CATALOG.get(k, {}).get("desc", k)).classes("text-caption text-grey")


def _set_sense(session: DesignSession, key: str, sense: str) -> None:
    senses = dict(session.pareto_obj_senses)
    senses[key] = sense
    session.pareto_obj_senses = senses
