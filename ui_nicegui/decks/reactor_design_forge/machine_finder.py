"""Machine Finder panel — hybrid search + workbench (Phase 14)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.forge_machine_finder_helpers import (
    FORGE_BOUND_FRACS,
    FORGE_DEFAULT_VAR_KEYS,
    FORGE_INTENT_LABELS,
    all_var_key_options,
    anchor_from_session,
    archive_table_rows,
    compute_bounds,
    intent_from_label,
    lens_contract,
    load_objective_packs,
    objectives_for_pack,
    promote_archive_row,
    resistance_atlas_rows,
    run_machine_finder,
    summarize_workbench_run,
)
from ui_nicegui.session import DesignSession


def render_machine_finder(
    session: DesignSession,
    *,
    review_mode: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Machine Finder").classes("text-subtitle1")
    ui.label(
        "Hybrid global → surrogate → local refinement. All candidates audited by the frozen evaluator. "
        "No relaxation; no auto-apply."
    ).classes("text-caption text-grey q-mb-sm")

    if review_mode:
        ui.label("Review Mode: setup and run controls locked — inspect archive and exports only.").classes(
            "text-orange q-mb-sm"
        )
        _render_workbench(session, on_complete=on_complete)
        return

    base = session.build_point_inputs()
    anchor = anchor_from_session(base)
    intent = intent_from_label(session.forge_mf_intent_label)
    var_options = all_var_key_options(anchor)

    with ui.expansion("Intent & lens", icon="tune").classes("w-full q-mb-sm"):
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

    with ui.expansion("Search space", icon="grid_on").classes("w-full q-mb-sm"):
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

    with ui.expansion("Run budget", icon="speed").classes("w-full q-mb-sm"):
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
            ui.notify(
                f"Run complete — archive {len(run_rep.get('archive') or [])} candidates",
                type="positive",
            )
            _render_workbench.refresh()
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

    _render_workbench(session, on_complete=on_complete)


@ui.refreshable
def _render_workbench(session: DesignSession, *, on_complete: Optional[Callable[[], None]] = None) -> None:
    run_rep = session.forge_workbench_run
    summary = summarize_workbench_run(run_rep)
    if not summary.get("loaded"):
        empty_state("No Machine Finder run yet. Configure and run, or restore a capsule.", kind="info")
        return

    ui.separator().classes("q-my-md")
    ui.label("Forge Workbench").classes("text-subtitle1")

    with ui.row().classes("w-full gap-4 flex-wrap"):
        with ui.card().classes("p-3"):
            ui.label("Run contract").classes("text-caption text-grey")
            ui.label(f"Intent: {summary.get('intent')}").classes("text-body2")
            ui.label(f"Trace evals: {summary.get('n_trace')}").classes("text-caption")
        with ui.card().classes("p-3"):
            ui.label("Archive").classes("text-caption text-grey")
            ui.label(
                f"{summary.get('n_feasible_archive')}/{summary.get('n_archive')} feasible · "
                f"{summary.get('n_dominant')} dominant"
            ).classes("text-body2")
        with ui.card().classes("p-3"):
            ui.label("Resistance").classes("text-caption text-grey")
            ui.label(f"Top blocker: {summary.get('top_blocker')}").classes("text-body2")
            ui.label(f"Dominant: {summary.get('dominant_resistance')}").classes("text-caption")

    rows = archive_table_rows(run_rep)
    if rows:
        with ui.expansion("Candidate archive", icon="inventory_2").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "idx", "label": "#", "field": "idx"},
                    {"name": "feasible", "label": "OK", "field": "feasible"},
                    {"name": "score", "label": "Score", "field": "score"},
                    {"name": "failure_mode", "label": "Failure", "field": "failure_mode", "align": "left"},
                    {"name": "min_margin", "label": "Min margin", "field": "min_margin"},
                    {"name": "R0_m", "label": "R0", "field": "R0_m"},
                    {"name": "Bt_T", "label": "Bt", "field": "Bt_T"},
                    {"name": "Ip_MA", "label": "Ip", "field": "Ip_MA"},
                    {"name": "Paux_MW", "label": "Paux", "field": "Paux_MW"},
                ],
                rows=rows,
                row_key="idx",
                pagination={"rowsPerPage": 10},
            ).classes("w-full")

            pick = ui.number("Promote row #", value=0, min=0, max=max(len(rows) - 1, 0), step=1)

            def _promote() -> None:
                try:
                    session.inputs = promote_archive_row(session.inputs, run_rep, int(pick.value or 0))
                    ui.notify("Promoted archive row to Point Designer inputs.", type="positive")
                except Exception as exc:
                    ui.notify(f"Promote failed: {exc}", type="negative")

            ui.button("Promote to Point Designer", icon="upload", on_click=_promote).props("outline flat")

    atlas_rows = resistance_atlas_rows(run_rep)
    if atlas_rows:
        with ui.expansion("Resistance atlas (trace)", icon="map").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                    {"name": "count", "label": "Count", "field": "count"},
                    {"name": "fraction", "label": "Share", "field": "fraction"},
                ],
                rows=atlas_rows,
                row_key="constraint",
            ).classes("w-full")

    rr = run_rep.get("resistance_report")
    if isinstance(rr, dict):
        with ui.expansion("Resistance report (JSON)", icon="description").classes("w-full"):
            ui.json(rr)
