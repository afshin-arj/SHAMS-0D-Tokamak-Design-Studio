"""Systems Mode — seeded feasibility recovery with advanced controls."""

from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.lib.systems_recovery_helpers import (
    BASE_DESIGN_VARIABLES,
    BASE_LABELS,
    build_recovery_seed,
    default_base_bounds,
    merge_recovery_bounds,
    recovery_distance_weights,
)
from ui_nicegui.lib.systems_state_helpers import append_journal, resolve_systems_problem
from ui_nicegui.lib.systems_workflow_helpers import (
    append_run_card,
    apply_x_to_session,
    artifact_from_recovery as build_solve_artifact,
    run_seeded_recovery,
    systems_run_payload,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

_SEED_MODES = ["Point Designer baseline", "Midpoint of bounds", "Manual seed editor"]


def render_recover_panel(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Seeded feasibility recovery").classes("text-subtitle1")
    ui.label(
        "Search for a nearby feasible point within declared bounds. "
        "Feasibility first; closeness to seed second — this is not an optimizer."
    ).classes("text-caption q-mb-sm")

    base, _, variables = resolve_systems_problem(session)
    if not variables:
        ui.markdown("Configure iteration variables on **1 · Targets** first.").classes("text-orange")
        return

    ui.checkbox(
        "Auto-trigger after infeasible precheck",
        value=session.systems_recovery_auto,
        on_change=lambda e: setattr(session, "systems_recovery_auto", bool(e.value)),
    )

    with ui.row().classes("gap-4 flex-wrap"):
        ui.number(
            "Evaluation budget",
            value=session.systems_recovery_budget,
            min=30,
            max=2000,
            on_change=lambda e: setattr(session, "systems_recovery_budget", int(e.value or 120)),
        ).classes("w-32")
        ui.number(
            "Local refinement steps",
            value=session.systems_recovery_local_steps,
            min=10,
            max=400,
            on_change=lambda e: setattr(session, "systems_recovery_local_steps", int(e.value or 40)),
        ).classes("w-32")
        ui.number(
            "Multi-start draws",
            value=session.systems_recovery_multistart,
            min=0,
            max=400,
            on_change=lambda e: setattr(session, "systems_recovery_multistart", int(e.value or 20)),
        ).classes("w-32")
        ui.number(
            "Random seed",
            value=session.systems_recovery_seed,
            min=0,
            max=999999,
            on_change=lambda e: setattr(session, "systems_recovery_seed", int(e.value or 2026)),
        ).classes("w-28")

    ui.select(
        _SEED_MODES,
        label="Seed source",
        value=session.systems_recovery_seed_mode if session.systems_recovery_seed_mode in _SEED_MODES else _SEED_MODES[0],
        on_change=lambda e: setattr(session, "systems_recovery_seed_mode", str(e.value)),
    ).classes("w-full q-mt-sm")

    ui.checkbox(
        "Include base design variables in recovery search",
        value=session.systems_recovery_basevars_enabled,
        on_change=lambda e: setattr(session, "systems_recovery_basevars_enabled", bool(e.value)),
    ).classes("q-mt-sm")

    if session.systems_recovery_basevars_enabled:
        opts = [k for k, _ in BASE_DESIGN_VARIABLES]
        ui.select(
            opts,
            label="Base variables to adjust",
            value=session.systems_recovery_basevars or [],
            multiple=True,
            on_change=lambda e: setattr(session, "systems_recovery_basevars", list(e.value or [])),
        ).classes("w-full")
        ui.label("Set explicit bounds per base variable; pin variables to keep them near the seed.").classes(
            "text-caption q-mb-sm"
        )
        _render_base_bounds(session, base)

    bounds = merge_recovery_bounds(session, base, variables)
    if session.systems_recovery_seed_mode == "Manual seed editor":
        _render_manual_seed(session, bounds)

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        if session.systems_recovery_running:
            ui.notify("Recovery already running", type="warning")
            return
        locked, task, is_owner = runlock_status("SystemsMode")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Systems Mode: Seeded recovery", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        session.systems_recovery_running = True
        ui.notify("Running seeded recovery…", type="info")
        try:
            b, _, v = resolve_systems_problem(session)
            bounds_rec = merge_recovery_bounds(session, b, v)
            mode_map = {
                "Point Designer baseline": "point_designer",
                "Midpoint of bounds": "midpoint",
                "Manual seed editor": "manual",
            }
            seed = build_recovery_seed(
                session,
                b,
                bounds_rec,
                mode=mode_map.get(session.systems_recovery_seed_mode, "point_designer"),
            )
            weights = recovery_distance_weights(session)
            rep = await run.io_bound(
                run_seeded_recovery,
                b,
                v,
                seed=seed,
                weights=weights or None,
                variables_bounds=bounds_rec,
                rng_seed=session.systems_recovery_seed,
                budget_evals=session.systems_recovery_budget,
                local_steps=session.systems_recovery_local_steps,
                multi_start=session.systems_recovery_multistart,
            )
            session.systems_recovery_last = rep
            art = build_solve_artifact(rep, design_intent=session.design_intent, base=b)
            session.systems_last_solve_artifact = art
            append_run_card(
                session,
                kind="SeededRecovery",
                settings={
                    "seed_mode": session.systems_recovery_seed_mode,
                    "budget": session.systems_recovery_budget,
                    "rng_seed": session.systems_recovery_seed,
                },
                outcome={"ok": bool(rep.get("ok")), "reason": str(rep.get("reason", ""))},
                payload=systems_run_payload(session, art),
            )
            append_journal(session, "SeededRecovery", {"ok": bool(rep.get("ok"))})
            ui.notify(
                "Recovery found feasible point" if rep.get("ok") else "Recovery best-effort complete",
                type="positive" if rep.get("ok") else "warning",
            )
            _results.refresh()
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Recovery failed: {exc}", type="negative")
        finally:
            session.systems_recovery_running = False
            runlock_release("SystemsMode")

    def _apply_best_to_inputs() -> None:
        rep = session.systems_recovery_last
        if not isinstance(rep, dict) or not isinstance(rep.get("best_point"), dict):
            ui.notify("No recovery best point", type="warning")
            return
        applied = apply_x_to_session(session, rep["best_point"])
        from ui_nicegui.lib.pd_handoff import navigate_to_point_designer

        navigate_to_point_designer(session)
        ui.notify(
            f"Applied {len(applied)} variables — KPIs STALE until Evaluate Point.",
            type="positive",
        )

    ui.button("Run seeded recovery", icon="healing", on_click=_run).props("outline q-mt-sm")
    ui.button("Apply best point → Point Designer", icon="input", on_click=_apply_best_to_inputs).props("flat q-ml-sm")
    _results(session)


def _render_base_bounds(session: DesignSession, base) -> None:
    stored = dict(session.systems_recovery_base_bounds or {})
    selected = list(session.systems_recovery_basevars or [])

    def _update(key: str, field: str, value) -> None:
        bb = dict(session.systems_recovery_base_bounds or {})
        entry = dict(bb.get(key) or {})
        dlo, dhi = default_base_bounds(base, key)
        entry.setdefault("lo", dlo)
        entry.setdefault("hi", dhi)
        entry[field] = value
        bb[key] = entry
        session.systems_recovery_base_bounds = bb

    with ui.expansion("Base-variable bounds", icon="tune").classes("w-full"):
        for key in selected:
            dlo, dhi = default_base_bounds(base, key)
            entry = stored.get(key) if isinstance(stored.get(key), dict) else {}
            label = BASE_LABELS.get(key, key)
            ui.number(
                f"{label} min",
                value=float(entry.get("lo", dlo)),
                on_change=lambda e, k=key: _update(k, "lo", float(e.value or 0)),
            ).classes("w-full")
            ui.number(
                f"{label} max",
                value=float(entry.get("hi", dhi)),
                on_change=lambda e, k=key: _update(k, "hi", float(e.value or 0)),
            ).classes("w-full")
            ui.checkbox(
                "Pin near seed",
                value=bool(entry.get("pin", False)),
                on_change=lambda e, k=key: _update(k, "pin", bool(e.value)),
            )


def _render_manual_seed(session: DesignSession, bounds: dict) -> None:
    with ui.expansion("Manual seed values", icon="edit").classes("w-full"):
        for key, b in bounds.items():
            lo = float(b.get("lo", 0.0))
            hi = float(b.get("hi", 1.0))
            mid = 0.5 * (lo + hi)
            manual = dict(session.systems_recovery_manual_seed or {})
            val = float(manual.get(key, mid))

            def _set(e, k=key, lo_b=lo, hi_b=hi):
                m = dict(session.systems_recovery_manual_seed or {})
                m[k] = max(lo_b, min(hi_b, float(e.value or mid)))
                session.systems_recovery_manual_seed = m

            ui.number(
                BASE_LABELS.get(key, key),
                value=val,
                min=lo,
                max=hi,
                on_change=_set,
            ).classes("w-full")


@ui.refreshable
def _results(session: DesignSession) -> None:
    rep = session.systems_recovery_last
    if not isinstance(rep, dict):
        return
    dist = rep.get("best_distance")
    dist_s = f"{float(dist):.4g}" if isinstance(dist, (int, float)) and dist == dist else "-"
    ui.label(
        f"Result: {rep.get('reason', '-')} | feasible={rep.get('ok')} | "
        f"evaluations={rep.get('evals', '-')} | distance={dist_s}"
    ).classes("text-body2 q-mt-sm")
    if isinstance(rep.get("best_point"), dict):
        with ui.expansion("Best point (recovery variables)", icon="place"):
            render_json_blob(rep["best_point"])

    trace = rep.get("trace")
    if isinstance(trace, list) and trace:
        with ui.expansion("Recovery search trace", icon="show_chart").classes("w-full"):
            try:
                import plotly.graph_objects as go

                xs = list(range(len(trace)))
                ys = [float(t.get("V", 0)) for t in trace if isinstance(t, dict)]
                feas = [bool(t.get("feasible")) for t in trace if isinstance(t, dict)]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=xs[: len(ys)], y=ys, mode="lines+markers", name="Violation score V"))
                fig.update_layout(
                    title="Recovery progress (lower V → more feasible)",
                    height=280,
                    margin=dict(l=40, r=20, t=40, b=40),
                    xaxis_title="Evaluation index",
                    yaxis_title="V",
                )
                ui.plotly(fig).classes("w-full")
                ui.label(f"Feasible evaluations: {sum(feas)} / {len(feas)}").classes("text-caption")
            except Exception:
                ui.code(str(trace[:20]))
