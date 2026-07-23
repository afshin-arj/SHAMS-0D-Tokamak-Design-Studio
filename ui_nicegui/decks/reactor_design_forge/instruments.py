"""Forge Instruments tab — grouped expert cockpit (full Streamlit parity)."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.forge_instrument_data import ALL_INSTRUMENTS, INSTRUMENT_CAPTIONS, INSTRUMENT_GROUPS
from ui_nicegui.lib.forge_instrument_engine import (
    ForgeContext,
    build_context,
    compute_instrument,
    filter_archive,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_instruments_tab(
    session: DesignSession,
    *,
    review_mode: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    run_rep = session.forge_workbench_run
    if not isinstance(run_rep, dict) or run_rep.get("archive") is None:
        empty_state(
            "No Machine Finder archive. Run **Setup & Search** or restore a capsule first.",
            kind="info",
        )
        ui.button(
            "Go to Setup & Search",
            icon="settings",
            on_click=lambda: (
                setattr(session, "forge_workflow_step", "2 · Setup & Search"),
                on_complete() if on_complete else None,
            ),
        ).props("outline").classes("q-mt-sm")
        return

    ui.label("Expert instruments").classes("text-subtitle1")
    ui.label(
        "All Forge workbench views from the legacy UI — grouped by task. "
        "Descriptive only; nothing auto-applies."
    ).classes("text-caption text-grey q-mb-sm")

    _render_archive_filters(session)

    groups = list(INSTRUMENT_GROUPS.keys())
    if session.forge_instrument_group not in groups:
        session.forge_instrument_group = groups[0]
    tools = INSTRUMENT_GROUPS.get(session.forge_instrument_group, [])
    if session.forge_instrument_tool not in tools:
        session.forge_instrument_tool = tools[0] if tools else ""

    grp_sel = ui.select(
        groups,
        label="Instrument category",
        value=session.forge_instrument_group,
    ).classes("w-full")

    tool_sel = ui.select(
        tools,
        label="Instrument",
        value=session.forge_instrument_tool,
    ).classes("w-full q-mb-sm")

    def _sync_group(g: str) -> None:
        session.forge_instrument_group = g
        tlist = INSTRUMENT_GROUPS.get(g, [])
        session.forge_instrument_tool = tlist[0] if tlist else ""
        tool_sel.set_options(tlist, value=session.forge_instrument_tool)
        _render_body.refresh()

    grp_sel.on("update:model-value", lambda e: _sync_group(str(e.value)))

    def _sync_tool(t: str) -> None:
        session.forge_instrument_tool = t
        _render_body.refresh()

    tool_sel.on("update:model-value", lambda e: _sync_tool(str(e.value)))

    cap = INSTRUMENT_CAPTIONS.get(session.forge_instrument_tool, "")
    if cap:
        ui.label(cap).classes("text-caption q-mb-sm")

    _render_body(session, review_mode=review_mode)


@ui.refreshable
def _render_body(session: DesignSession, *, review_mode: bool = False) -> None:
    ctx = build_context(session)
    tool = str(session.forge_instrument_tool or "")
    if tool not in ALL_INSTRUMENTS:
        empty_state("Select an instrument.", kind="info")
        return

    if _needs_candidate_picker(tool):
        _candidate_picker(session, ctx)
    if tool == "Boundary navigator":
        _boundary_navigator_controls(session, ctx)
    if tool == "Provenance graph":
        ui.input(
            "Constraint name",
            value=session.forge_provenance_constraint,
            on_change=lambda e: setattr(session, "forge_provenance_constraint", str(e.value or "q_div")),
        ).classes("w-full q-mb-sm")
    if tool == "Local cartography":
        _local_cartography_controls(session, ctx, review_mode)
    if tool == "Uncertainty (Monte Carlo)":
        _monte_carlo_controls(session, ctx, review_mode)
    if tool == "Casebook runner":
        _casebook_controls(session, ctx, review_mode)
    if tool == "Collaboration (review sessions)":
        _collaboration_controls(session, ctx, review_mode)

    view = compute_instrument(tool, ctx)
    if view.error:
        ui.label(view.error).classes("text-orange")
    if view.caption:
        ui.label(view.caption).classes("text-caption q-mb-xs")
    if view.kpis:
        kpi_row(view.kpis)
    if view.markdown:
        ui.markdown(view.markdown).classes("q-mb-sm")
    if view.table_rows and view.table_columns:
        ui.table(
            columns=view.table_columns,
            rows=view.table_rows,
            row_key=view.table_row_key or "idx",
            pagination={"rowsPerPage": 12},
        ).classes("w-full q-mb-sm")
    if view.json_blob is not None:
        with ui.expansion("Structured data", icon="data_object", value=bool(view.json_expanded)).classes("w-full"):
            render_json_blob(view.json_blob)
    if view.download:
        data, fname, mime = view.download
        ui.download_button(f"Download {fname}", data=data, file_name=fname).props(f'mime-type="{mime}"')

    if tool == "Trace telemetry":
        from ui_nicegui.lib.forge_viz_helpers import trace_score_figure

        fig = trace_score_figure(ctx.trace)
        if fig:
            ui.plotly(fig).classes("w-full q-mt-sm")
    if tool == "Local cartography" and session.forge_localcart_df:
        from ui_nicegui.lib.forge_viz_helpers import local_cartography_figure

        rows = session.forge_localcart_df if isinstance(session.forge_localcart_df, list) else []
        fig = local_cartography_figure(rows)
        if fig:
            ui.plotly(fig).classes("w-full q-mt-sm")


def _render_archive_filters(session: DesignSession) -> None:
    with ui.expansion("Archive filters (apply to instruments)", icon="filter_list").classes("w-full q-mb-sm"):
        ui.checkbox(
            "Keep only margin ≥ 0",
            value=session.forge_filter_robust,
            on_change=lambda e: setattr(session, "forge_filter_robust", bool(e.value)),
        )
        ui.number(
            "Min score (optional)",
            value=session.forge_filter_min_score if session.forge_filter_min_score > -1e29 else None,
            on_change=lambda e: setattr(
                session,
                "forge_filter_min_score",
                float(e.value) if e.value is not None else float("-inf"),
            ),
        ).classes("w-full")
        ui.number(
            "Max COE proxy (USD/MWh, optional)",
            value=session.forge_filter_max_coe,
            min=0.0,
            step=10.0,
            on_change=lambda e: setattr(
                session,
                "forge_filter_max_coe",
                float(e.value) if e.value is not None else None,
            ),
        ).classes("w-full")


def _needs_candidate_picker(tool: str) -> bool:
    return tool in {
        "Machine dossier",
        "Review Trinity",
        "Attack simulation",
        "Closure certificate",
        "Reactor accounting console",
        "Margin ledger",
        "Reality gates",
        "Engineering reality budget",
        "Failure-mode canon",
        "Economics deck",
        "Report pack",
        "Design narrative",
        "Design card",
        "Design packet",
        "Design class",
        "Citation blocks",
        "Reference reproduction",
        "Reviewer packet",
        "Scan ↔ Forge grounding",
        "Inverse design / Why not?",
        "Counterfactual lens",
        "Confidence sweep",
        "Sensitivity fingerprint",
        "Do-not-build brief",
        "Paper-ready signals",
        "Provenance graph",
    }


def _candidate_picker(session: DesignSession, ctx: ForgeContext) -> None:
    filt = ctx.filtered_archive
    if not filt:
        ui.label("No candidates after filters.").classes("text-orange q-mb-sm")
        return
    max_idx = len(filt) - 1
    idx = min(max(int(session.forge_inspect_idx or 0), 0), max_idx)
    session.forge_inspect_idx = idx
    ui.number(
        "Candidate index (filtered archive order)",
        value=idx,
        min=0,
        max=max_idx,
        step=1,
        on_change=lambda e: (
            setattr(session, "forge_inspect_idx", int(e.value or 0)),
            _render_body.refresh(),
        ),
    ).classes("w-48 q-mb-sm")


def _boundary_navigator_controls(session: DesignSession, ctx: ForgeContext) -> None:
    names = ctx.constraint_names
    if not names:
        return
    if session.forge_surface_constraint not in names:
        session.forge_surface_constraint = names[0]
    ui.select(
        names,
        label="Constraint for surface map",
        value=session.forge_surface_constraint,
        on_change=lambda e: setattr(session, "forge_surface_constraint", str(e.value)),
    ).classes("w-full q-mb-sm")


def _local_cartography_controls(session: DesignSession, ctx: ForgeContext, review_mode: bool) -> None:
    vkeys = ctx.var_keys
    if len(vkeys) < 2:
        return
    with ui.row().classes("gap-2 flex-wrap w-full"):
        x_sel = ui.select(vkeys, label="X", value=session.forge_localcart_x or vkeys[0]).classes("flex-1")
        y_sel = ui.select(vkeys, label="Y", value=session.forge_localcart_y or vkeys[min(1, len(vkeys) - 1)]).classes("flex-1")
        span_sl = ui.slider(min=5, max=60, value=session.forge_localcart_span, step=5).classes("flex-1")
        grid_sl = ui.slider(min=9, max=41, value=session.forge_localcart_grid, step=2).classes("flex-1")

    def _sync_local() -> None:
        session.forge_localcart_x = str(x_sel.value)
        session.forge_localcart_y = str(y_sel.value)
        session.forge_localcart_span = int(span_sl.value or 20)
        session.forge_localcart_grid = int(grid_sl.value or 21)

    for w in (x_sel, y_sel, span_sl, grid_sl):
        w.on("update:model-value", lambda: _sync_local())

    async def _run_local() -> None:
        from ui_nicegui.lib.forge_helpers import FORGE_RUNLOCK_OWNER
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        if review_mode:
            ui.notify("Review Mode: cartography disabled", type="warning")
            return
        locked, task, is_owner = runlock_status(FORGE_RUNLOCK_OWNER)
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Reactor Design Forge: Local cartography", FORGE_RUNLOCK_OWNER):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        from ui_nicegui.lib.forge_instrument_engine import run_local_cartography

        try:
            df = await run.io_bound(run_local_cartography, ctx, session)
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.forge_localcart_df = df
            ui.notify("Local cartography complete", type="positive")
            _render_body.refresh()
        except Exception as exc:
            ui.notify(f"Cartography failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                runlock_release(FORGE_RUNLOCK_OWNER, lease)

    ui.button("Run local cartography", icon="grid_on", on_click=_run_local).props("outline q-mb-sm")


def _monte_carlo_controls(session: DesignSession, ctx: ForgeContext, review_mode: bool) -> None:
    ns_in = ui.number("Samples", value=session.forge_uq_samples, min=20, max=2000, step=20).classes("w-32")
    pct_sl = ui.slider(min=1, max=25, value=session.forge_uq_pct, step=1).classes("w-full")

    def _sync_uq() -> None:
        session.forge_uq_samples = int(ns_in.value or 200)
        session.forge_uq_pct = int(pct_sl.value or 5)

    ns_in.on("update:model-value", lambda: _sync_uq())
    pct_sl.on("update:model-value", lambda: _sync_uq())

    async def _run_uq() -> None:
        from ui_nicegui.lib.forge_helpers import FORGE_RUNLOCK_OWNER
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        if review_mode:
            ui.notify("Review Mode: UQ disabled", type="warning")
            return
        locked, task, is_owner = runlock_status(FORGE_RUNLOCK_OWNER)
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Reactor Design Forge: Robustness MC", FORGE_RUNLOCK_OWNER):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        from ui_nicegui.lib.forge_instrument_engine import run_robustness_mc

        try:
            uq = await run.io_bound(run_robustness_mc, ctx, session)
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.forge_uq_result = uq
            ui.notify("Monte Carlo complete", type="positive")
            _render_body.refresh()
        except Exception as exc:
            ui.notify(f"Monte Carlo failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                runlock_release(FORGE_RUNLOCK_OWNER, lease)

    ui.button("Run robustness Monte Carlo", icon="casino", on_click=_run_uq).props("outline q-mb-sm")


def _casebook_controls(session: DesignSession, ctx: ForgeContext, review_mode: bool) -> None:
    ui.input("Case name", value=f"Case {len(session.forge_casebook) + 1}").classes("w-full")

    async def _add_case() -> None:
        name = f"Case {len(session.forge_casebook) + 1}"
        session.forge_casebook = list(session.forge_casebook or []) + [
            {"name": name, "lens": session.forge_mf_pack_name or "default", "seed": int(ctx.run.get("seed", 1) or 1)},
        ]
        ui.notify("Case added", type="positive")
        _render_body.refresh()

    async def _run_casebook() -> None:
        from ui_nicegui.lib.forge_helpers import FORGE_RUNLOCK_OWNER
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        if review_mode:
            ui.notify("Review Mode: casebook run disabled", type="warning")
            return
        book = session.forge_casebook or []
        if len(book) < 1:
            ui.notify("Add at least one case", type="warning")
            return
        locked, task, is_owner = runlock_status(FORGE_RUNLOCK_OWNER)
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Reactor Design Forge: Casebook", FORGE_RUNLOCK_OWNER):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        from ui_nicegui.lib.forge_machine_finder_helpers import run_machine_finder, compute_bounds, objectives_for_pack

        results = []
        base = session.build_point_inputs()
        anchor = {k: float(getattr(base, k)) for k in ("R0_m", "Bt_T", "Ip_MA", "Paux_MW") if hasattr(base, k)}
        var_keys = list(session.forge_mf_var_keys or ["R0_m", "Bt_T", "Ip_MA", "Paux_MW"])
        bounds = compute_bounds(anchor, var_keys, bound_mode=session.forge_mf_bound_mode, custom_bounds=session.forge_mf_custom_bounds)
        intent = str(ctx.intent)
        objectives = objectives_for_pack(intent, session.forge_mf_pack_name)
        try:
            for case in book[:5]:
                try:
                    rep = await run.io_bound(
                        run_machine_finder,
                        intent=intent,
                        anchor=anchor,
                        var_keys=var_keys,
                        bounds=bounds,
                        objectives=objectives,
                        pop_size=32,
                        generations=15,
                        surrogate_rounds=2,
                        local_steps=20,
                        archive_topk=20,
                        require_feasible_only=True,
                        seed=int(case.get("seed", 1)),
                    )
                    if not lease_valid(lease):
                        ui.notify("Run was force-cleared — discarding results.", type="warning")
                        return
                    tr = rep.get("trace") or []
                    results.append({
                        "case": case.get("name"),
                        "lens": case.get("lens"),
                        "n_eval": len(tr),
                        "n_feasible": sum(1 for t in tr if t.get("feasible")),
                    })
                except Exception as exc:
                    results.append({"case": case.get("name"), "lens": case.get("lens"), "n_eval": 0, "n_feasible": 0, "error": str(exc)})
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.forge_casebook_results = results
            ui.notify("Casebook run complete", type="positive")
            _render_body.refresh()
        finally:
            if lease_valid(lease):
                runlock_release(FORGE_RUNLOCK_OWNER, lease)

    with ui.row().classes("gap-2"):
        ui.button("Add case", icon="add", on_click=_add_case).props("outline")
        ui.button("Run casebook (≤5 cases)", icon="play_arrow", on_click=_run_casebook).props("outline")


def _collaboration_controls(session: DesignSession, ctx: ForgeContext, review_mode: bool) -> None:
    ui.label("Create, export, or import a review session (comments/votes over candidates).").classes("text-caption q-mb-sm")
    title_in = ui.input("Session title", value=f"Forge review — {ctx.intent}").classes("w-full")

    async def _new_session() -> None:
        try:
            from pathlib import Path
            from tools.sandbox.tier7 import new_review_session, repo_fingerprint

            root = Path(__file__).resolve().parents[3]
            fp = repo_fingerprint(root)
            sess = new_review_session(
                title=str(title_in.value or "Forge review"),
                evaluator_fp=fp,
                intent=ctx.intent,
                notes="Created from NiceGUI Forge Instruments",
            )
            sess.candidates = [
                {"idx": i, "feasible": a.get("feasible"), "score": a.get("_score")}
                for i, a in enumerate((ctx.filtered_archive or ctx.archive)[:40])
            ]
            session.forge_review_session = sess.to_dict()
            ui.notify("Review session created", type="positive")
            _render_body.refresh()
        except Exception as exc:
            ui.notify(f"Session create failed: {exc}", type="negative")

    async def _export_zip() -> None:
        rs = session.forge_review_session
        if not isinstance(rs, dict):
            ui.notify("Create a session first", type="warning")
            return
        try:
            from tools.sandbox.tier7 import ReviewSession, export_review_session_zip

            blob = export_review_session_zip(ReviewSession.from_dict(rs))
            ui.download(blob, "review_session.zip")
        except Exception as exc:
            ui.notify(f"Export failed: {exc}", type="negative")

    async def _import_upload(e) -> None:
        try:
            from tools.sandbox.tier7 import import_review_session_zip

            data = e.content.read()
            sess = import_review_session_zip(data)
            session.forge_review_session = sess.to_dict()
            ui.notify("Review session imported", type="positive")
            _render_body.refresh()
        except Exception as exc:
            ui.notify(f"Import failed: {exc}", type="negative")

    with ui.row().classes("gap-2 flex-wrap"):
        ui.button("New session", icon="add", on_click=_new_session).props("outline")
        ui.button("Export ZIP", icon="download", on_click=_export_zip).props("outline")
    ui.upload(on_upload=_import_upload).props('accept=".zip" auto-upload label="Import review session ZIP"').classes("w-full q-mt-sm")
