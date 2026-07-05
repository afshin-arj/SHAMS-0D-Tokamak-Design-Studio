"""Machine Finder — Setup & Search tab (run only; workbench is tab 3)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.forge_machine_finder_helpers import (
    FORGE_BOUND_FRACS,
    FORGE_DEFAULT_VAR_KEYS,
    FORGE_INTENT_LABELS,
    all_var_key_options,
    anchor_from_session,
    compute_bounds,
    intent_from_label,
    lens_contract,
    load_objective_packs,
    objectives_for_pack,
    run_machine_finder,
    summarize_workbench_run,
)
from ui_nicegui.session import DesignSession


def render_machine_finder(
    session: DesignSession,
    *,
    review_mode: bool = False,
    flat: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Machine Finder").classes("text-subtitle1")
    ui.label(
        "Hybrid global → surrogate → local refinement. All candidates audited by the frozen evaluator. "
        "No relaxation; no auto-apply."
    ).classes("text-caption text-grey q-mb-sm")

    wb = summarize_workbench_run(session.forge_workbench_run)
    if wb.get("loaded"):
        ui.label(
            f"Last run: {wb.get('n_feasible_archive')}/{wb.get('n_archive')} feasible · "
            f"top blocker {wb.get('top_blocker')} — open **Workbench** tab to inspect."
        ).classes("text-caption text-positive q-mb-sm")

    if review_mode:
        ui.label("Review Mode: setup and run controls locked.").classes("text-orange q-mb-sm")
        return

    base = session.build_point_inputs()
    anchor = anchor_from_session(base)
    intent = intent_from_label(session.forge_mf_intent_label)
    var_options = all_var_key_options(anchor)

    def _panel(title: str, icon: str):
        if flat:
            ui.label(title).classes("text-subtitle2 q-mt-sm")
            return ui.column().classes("w-full")
        return ui.expansion(title, icon=icon).classes("w-full q-mb-sm")

    with _panel("Intent & lens", "tune"):
        ui.select(
            FORGE_INTENT_LABELS,
            label="Design intent",
            value=session.forge_mf_intent_label,
            on_change=lambda e: setattr(session, "forge_mf_intent_label", str(e.value)),
        ).classes("w-full")
        packs = load_objective_packs(intent)
        pack_names = [p.name for p in packs] + ["Custom (manual objectives)"]
        if session.forge_mf_pack_name not in pack_names:
            session.forge_mf_pack_name = pack_names[0]
        ui.select(
            pack_names,
            label="Objective pack",
            value=session.forge_mf_pack_name,
            on_change=lambda e: setattr(session, "forge_mf_pack_name", str(e.value)),
        ).classes("w-full")

    with _panel("Search space", "grid_on"):
        ui.label("Variables the finder may change (frozen variables stay fixed).").classes("text-caption")
        keys = [k for k in (session.forge_mf_var_keys or FORGE_DEFAULT_VAR_KEYS) if k in var_options]
        if not keys:
            keys = [k for k in FORGE_DEFAULT_VAR_KEYS if k in var_options]

        def _sync_keys(e) -> None:
            session.forge_mf_var_keys = list(e.value or [])

        ui.select(
            var_options,
            label="Variables to optimize",
            value=keys,
            multiple=True,
            on_change=_sync_keys,
        ).classes("w-full")
        ui.select(
            list(FORGE_BOUND_FRACS.keys()) + ["Custom"],
            label="Bounds mode",
            value=session.forge_mf_bound_mode,
            on_change=lambda e: setattr(session, "forge_mf_bound_mode", str(e.value)),
        ).classes("w-full")

        if session.forge_mf_bound_mode == "Custom":
            ui.label("Custom bounds (per variable)").classes("text-caption")
            custom = dict(session.forge_mf_custom_bounds or {})
            for k in keys:
                lo, hi = compute_bounds(anchor, [k], bound_mode="Medium (±20%)")[k]
                if k in custom:
                    lo, hi = custom[k]
                with ui.row().classes("gap-2 items-center w-full"):
                    ui.label(k).classes("w-24 text-caption")
                    lo_in = ui.number("lo", value=lo, format="%.4g").classes("flex-1")
                    hi_in = ui.number("hi", value=hi, format="%.4g").classes("flex-1")

                    def _save_bound(key=k, lo_w=lo_in, hi_w=hi_in) -> None:
                        cb = dict(session.forge_mf_custom_bounds or {})
                        cb[key] = (float(lo_w.value or 0), float(hi_w.value or 0))
                        session.forge_mf_custom_bounds = cb

                    lo_in.on("update:model-value", lambda: _save_bound())
                    hi_in.on("update:model-value", lambda: _save_bound())

    with _panel("Advanced engine", "science"):
        ui.checkbox(
            "Constraint-surface surfing",
            value=session.forge_adv_surface,
            on_change=lambda e: setattr(session, "forge_adv_surface", bool(e.value)),
        )
        ui.checkbox(
            "Feasibility skeleton",
            value=session.forge_adv_skeleton,
            on_change=lambda e: setattr(session, "forge_adv_skeleton", bool(e.value)),
        )
        ui.checkbox(
            "Staged run (phase-by-phase)",
            value=session.forge_adv_staged,
            on_change=lambda e: setattr(session, "forge_adv_staged", bool(e.value)),
        )
        ui.number(
            "Min signed margin guard (optional)",
            value=session.forge_min_margin_guard,
            min=0.0,
            step=0.01,
            on_change=lambda e: setattr(session, "forge_min_margin_guard", float(e.value or 0)),
        ).classes("w-full")

    if session.forge_stage_state and isinstance(session.forge_stage_state, dict):
        _render_staged_phases(session, on_complete=on_complete)

    with _panel("Run budget", "speed"):
        with ui.row().classes("w-full gap-4 flex-wrap"):
            ui.number(
                "Pop size",
                value=session.forge_mf_pop_size,
                min=20,
                max=200,
                step=4,
                on_change=lambda e: setattr(session, "forge_mf_pop_size", int(e.value or 64)),
            ).classes("flex-1")
            ui.number(
                "Global generations",
                value=session.forge_mf_generations,
                min=5,
                max=200,
                step=5,
                on_change=lambda e: setattr(session, "forge_mf_generations", int(e.value or 40)),
            ).classes("flex-1")
            ui.number(
                "Surrogate rounds",
                value=session.forge_mf_surrogate_rounds,
                min=0,
                max=30,
                on_change=lambda e: setattr(session, "forge_mf_surrogate_rounds", int(e.value or 6)),
            ).classes("flex-1")
            ui.number(
                "Local steps",
                value=session.forge_mf_local_steps,
                min=0,
                max=300,
                on_change=lambda e: setattr(session, "forge_mf_local_steps", int(e.value or 70)),
            ).classes("flex-1")
        ui.slider(
            min=20,
            max=200,
            step=10,
            value=session.forge_mf_archive_topk,
            on_change=lambda e: setattr(session, "forge_mf_archive_topk", int(e.value)),
        ).props("label").classes("w-full")
        ui.label(f"Archive top-k: {session.forge_mf_archive_topk}").classes("text-caption")
        ui.checkbox(
            "Archive: keep feasible only (recommended)",
            value=session.forge_mf_require_feasible_only,
            on_change=lambda e: setattr(session, "forge_mf_require_feasible_only", bool(e.value)),
        )

    async def _run_finder() -> None:
        if session.forge_mf_running:
            ui.notify("Machine Finder already running", type="warning")
            return
        var_keys = list(session.forge_mf_var_keys or FORGE_DEFAULT_VAR_KEYS)
        if not var_keys:
            ui.notify("Select at least one variable", type="negative")
            return
        intent_local = intent_from_label(session.forge_mf_intent_label)
        anchor_local = anchor_from_session(session.build_point_inputs())
        bounds = compute_bounds(
            anchor_local,
            var_keys,
            bound_mode=session.forge_mf_bound_mode,
            custom_bounds=session.forge_mf_custom_bounds,
        )
        objectives = objectives_for_pack(intent_local, session.forge_mf_pack_name)
        session.forge_lens_contract = lens_contract(intent_local, session.forge_mf_pack_name, objectives)

        if session.forge_adv_staged:
            from tools.sandbox.hybrid_engine import VarSpec

            var_specs = [VarSpec(key=k, lo=float(bounds[k][0]), hi=float(bounds[k][1])) for k in var_keys]
            session.forge_stage_state = {
                "intent": intent_local,
                "anchor": dict(anchor_local),
                "var_specs": [v.__dict__ for v in var_specs],
                "objectives": [{"key": o.key, "sense": o.sense, "weight": float(o.weight)} for o in objectives],
                "budgets": {
                    "pop_size": int(session.forge_mf_pop_size),
                    "generations": int(session.forge_mf_generations),
                    "surrogate_rounds": int(session.forge_mf_surrogate_rounds),
                    "propose_per_round": 36,
                    "local_steps": int(session.forge_mf_local_steps),
                    "archive_topk": int(session.forge_mf_archive_topk),
                    "resistance_window": 250,
                    "surf_steps": 80,
                },
                "all_points": [],
                "trace": [],
                "done": {"global": False, "surrogate": False, "local": False, "surf": False},
                "seed": int(session.forge_mf_seed),
            }
            ui.notify("Staged run initialized — use phase buttons below.", type="info")
            if on_complete:
                on_complete()
            return

        session.forge_mf_running = True
        ui.notify("Machine Finder started…", type="info")
        try:
            run_rep = await run.io_bound(
                run_machine_finder,
                intent=intent_local,
                anchor=anchor_local,
                var_keys=var_keys,
                bounds=bounds,
                objectives=objectives,
                pop_size=int(session.forge_mf_pop_size),
                generations=int(session.forge_mf_generations),
                surrogate_rounds=int(session.forge_mf_surrogate_rounds),
                local_steps=int(session.forge_mf_local_steps),
                archive_topk=int(session.forge_mf_archive_topk),
                require_feasible_only=bool(session.forge_mf_require_feasible_only),
                seed=int(session.forge_mf_seed),
            )
            session.forge_workbench_run = run_rep
            session.forge_mf_last_bounds = {k: list(v) for k, v in bounds.items()}
            n = len(run_rep.get("archive") or [])
            ui.notify(
                f"Run complete — {n} archive candidates. Open **Workbench** tab to inspect.",
                type="positive",
            )
            if on_complete:
                on_complete()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Machine Finder failed: {exc}", type="negative")
        finally:
            session.forge_mf_running = False

    btn = ui.button("Run machine finder", icon="play_arrow", on_click=_run_finder).props("color=primary")
    if session.forge_mf_running:
        btn.props("disable")
        ui.spinner(size="lg").classes("q-ml-sm")


def _render_staged_phases(session: DesignSession, *, on_complete=None) -> None:
    ui.separator().classes("q-my-sm")
    ui.label("Staged run — execute phases one at a time").classes("text-subtitle2")
    stg = session.forge_stage_state
    if not isinstance(stg, dict):
        return
    done = stg.get("done") or {}

    async def _phase(name: str, fn, *args) -> None:
        try:
            pts, tr = await run.io_bound(fn, *args)
            stg["all_points"] = (stg.get("all_points") or []) + list(pts)
            stg["trace"] = (stg.get("trace") or []) + list(tr)
            done[name] = True
            stg["done"] = done
            session.forge_stage_state = stg
            _finalize_staged_run(session)
            ui.notify(f"{name.title()} phase complete", type="positive")
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Phase failed: {exc}", type="negative")

    with ui.row().classes("gap-2 flex-wrap"):
        if not done.get("global"):
            ui.button("Run Global", on_click=lambda: _phase("global", _staged_global, session)).props("outline")
        if done.get("global") and not done.get("surrogate"):
            ui.button("Run Surrogate", on_click=lambda: _phase("surrogate", _staged_surrogate, session)).props("outline")
        if done.get("global") and not done.get("local"):
            ui.button("Run Local", on_click=lambda: _phase("local", _staged_local, session)).props("outline")
        if done.get("local") and not done.get("surf"):
            ui.button("Run Surf", on_click=lambda: _phase("surf", _staged_surf, session)).props("outline")
    ui.label(f"Done: {', '.join(k for k, v in done.items() if v) or 'none'}").classes("text-caption")


def _staged_global(session: DesignSession):
    from tools.sandbox.hybrid_engine import VarSpec, Objective, global_de_phase

    stg = session.forge_stage_state
    eval_fn = _staged_eval_fn(session)
    var_specs = [VarSpec(**v) for v in (stg.get("var_specs") or [])]
    objectives = [Objective(**o) for o in (stg.get("objectives") or [])]
    budgets = stg.get("budgets") or {}
    return global_de_phase(
        evaluate_fn=eval_fn,
        anchor_inputs=stg.get("anchor") or {},
        var_specs=var_specs,
        objectives=objectives,
        pop_size=int(budgets.get("pop_size", 64)),
        generations=int(budgets.get("generations", 40)),
        seed=int(stg.get("seed", 1)),
    )


def _staged_surrogate(session: DesignSession):
    from tools.sandbox.hybrid_engine import VarSpec, Objective, surrogate_phase

    stg = session.forge_stage_state
    eval_fn = _staged_eval_fn(session)
    var_specs = [VarSpec(**v) for v in (stg.get("var_specs") or [])]
    objectives = [Objective(**o) for o in (stg.get("objectives") or [])]
    budgets = stg.get("budgets") or {}
    return surrogate_phase(
        evaluate_fn=eval_fn,
        anchor_inputs=stg.get("anchor") or {},
        var_specs=var_specs,
        objectives=objectives,
        seed=int(stg.get("seed", 1)),
        history=list(stg.get("all_points") or []),
        rounds=int(budgets.get("surrogate_rounds", 6)),
        propose_per_round=int(budgets.get("propose_per_round", 36)),
    )


def _staged_local(session: DesignSession):
    from tools.sandbox.hybrid_engine import VarSpec, Objective, local_refine_phase

    stg = session.forge_stage_state
    eval_fn = _staged_eval_fn(session)
    var_specs = [VarSpec(**v) for v in (stg.get("var_specs") or [])]
    objectives = [Objective(**o) for o in (stg.get("objectives") or [])]
    budgets = stg.get("budgets") or {}
    return local_refine_phase(
        evaluate_fn=eval_fn,
        anchor_inputs=stg.get("anchor") or {},
        var_specs=var_specs,
        objectives=objectives,
        seed=int(stg.get("seed", 1)),
        seeds=list(stg.get("all_points") or []),
        steps=int(budgets.get("local_steps", 70)),
    )


def _staged_surf(session: DesignSession):
    from tools.sandbox.hybrid_engine import VarSpec, Objective, surface_surf_phase

    stg = session.forge_stage_state
    eval_fn = _staged_eval_fn(session)
    var_specs = [VarSpec(**v) for v in (stg.get("var_specs") or [])]
    objectives = [Objective(**o) for o in (stg.get("objectives") or [])]
    budgets = stg.get("budgets") or {}
    return surface_surf_phase(
        evaluate_fn=eval_fn,
        anchor_inputs=stg.get("anchor") or {},
        var_specs=var_specs,
        objectives=objectives,
        seed=int(stg.get("seed", 1)),
        seeds=list(stg.get("all_points") or []),
        steps=int(budgets.get("surf_steps", 80)),
    )


def _staged_eval_fn(session: DesignSession):
    from ui_nicegui.lib.forge_machine_finder_helpers import make_evaluate_fn, objectives_for_pack

    stg = session.forge_stage_state or {}
    intent = str(stg.get("intent") or "Reactor")
    objectives = objectives_for_pack(intent, session.forge_mf_pack_name)
    return make_evaluate_fn(intent, objectives, min_margin=float(session.forge_min_margin_guard or 0))


def _finalize_staged_run(session: DesignSession) -> None:
    from tools.sandbox.hybrid_engine import VarSpec, build_archive, resistance_atlas, variable_correlations, build_feasibility_skeleton

    stg = session.forge_stage_state
    if not isinstance(stg, dict):
        return
    var_specs = [VarSpec(**v) for v in (stg.get("var_specs") or [])]
    budgets = stg.get("budgets") or {}
    archive = build_archive(list(stg.get("all_points") or []), var_specs, topk=int(budgets.get("archive_topk", 60)))
    trace = list(stg.get("trace") or [])
    run = {
        "kind": "optimization_sandbox_hybrid_run_staged",
        "intent": str(stg.get("intent")),
        "seed": int(stg.get("seed", 1)),
        "archive": archive,
        "trace": trace,
        "resistance": resistance_atlas(trace, last_n=int(budgets.get("resistance_window", 250))),
        "variable_correlations": variable_correlations(archive, var_specs),
        "var_specs": stg.get("var_specs"),
    }
    if session.forge_adv_skeleton:
        try:
            run["feasibility_skeleton"] = build_feasibility_skeleton(archive, var_specs)
        except Exception:
            pass
    session.forge_workbench_run = run

