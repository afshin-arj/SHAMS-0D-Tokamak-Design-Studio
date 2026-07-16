"""Forge Workbench tab — archive explore, candidate instruments, review bench."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.decks.reactor_design_forge.handoff_panel import render_archive_handoffs
from ui_nicegui.lib.forge_interpret_helpers import (
    archive_point,
    design_card_markdown,
    enrich_candidate_instruments,
    ladder_histogram_rows,
    scatter_axis_options,
    summarize_conflict_atlas,
    update_conflict_atlas,
    why_not_for_candidate,
)
from ui_nicegui.lib.forge_instrument_engine import compute_instrument, build_context
from ui_nicegui.lib.forge_labels import WORKBENCH_VIEWS
from ui_nicegui.lib.forge_machine_finder_helpers import (
    archive_table_rows,
    resistance_atlas_rows,
    summarize_workbench_run,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_forge_workbench(
    session: DesignSession,
    *,
    review_mode: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    run_rep = session.forge_workbench_run
    summary = summarize_workbench_run(run_rep)
    if not summary.get("loaded"):
        empty_state(
            "No Machine Finder archive yet. Run a search on **Setup & Search**, or restore a capsule.",
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

    if isinstance(run_rep, dict):
        rr = run_rep.get("resistance_report")
        session.forge_conflict_atlas = update_conflict_atlas(session.forge_conflict_atlas, rr)

    kpi_row([
        ("Intent", summary.get("intent", "-")),
        ("Archive", f"{summary.get('n_feasible_archive')}/{summary.get('n_archive')} OK"),
        ("Trace evals", str(summary.get("n_trace", "-"))),
        ("Top blocker", summary.get("top_blocker") or "-"),
    ])

    view = session.forge_wb_view if session.forge_wb_view in WORKBENCH_VIEWS else WORKBENCH_VIEWS[0]
    ui.select(
        WORKBENCH_VIEWS,
        label="Workbench view",
        value=view,
        on_change=lambda e: (
            setattr(session, "forge_wb_view", str(e.value)),
            _render_view_body.refresh(),
        ),
    ).classes("w-full q-mb-sm")

    _render_view_body(session, review_mode=review_mode, on_complete=on_complete)


@ui.refreshable
def _render_view_body(
    session: DesignSession,
    *,
    review_mode: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    run_rep = session.forge_workbench_run
    if not isinstance(run_rep, dict):
        return
    view = session.forge_wb_view if session.forge_wb_view in WORKBENCH_VIEWS else WORKBENCH_VIEWS[0]
    archive = run_rep.get("archive") or []
    intent = str(run_rep.get("intent") or session.forge_mf_intent_label)

    if view == "Archive overview":
        _render_archive_overview(session, run_rep, archive)
    elif view == "Candidate inspector":
        _render_candidate_inspector(session, archive, intent)
    elif view == "Machine dossier (compact)":
        ctx = build_context(session)
        v = compute_instrument("Machine dossier", ctx)
        if v.markdown:
            ui.markdown(v.markdown)
        if v.kpis:
            kpi_row(v.kpis)
        if v.json_blob is not None:
            render_json_blob(v.json_blob)
    elif view == "Resistance & conflicts":
        _render_resistance(session, run_rep)
    elif view == "Review bench":
        _render_review_bench(session, run_rep, archive, review_mode=review_mode, on_complete=on_complete)
    elif view == "Run dashboard":
        ctx = build_context(session)
        v = compute_instrument("Run dashboard", ctx)
        if v.kpis:
            kpi_row(v.kpis)
        if v.json_blob is not None:
            render_json_blob(v.json_blob)
    else:
        _render_ladder(session, archive)


def _render_archive_overview(session: DesignSession, run_rep: dict, archive: list) -> None:
    axis_opts = scatter_axis_options(archive)
    if not axis_opts:
        axis_opts = ["R0_m", "Bt_T"]
    if session.forge_scatter_x not in axis_opts:
        session.forge_scatter_x = axis_opts[0]
    if session.forge_scatter_y not in axis_opts:
        session.forge_scatter_y = axis_opts[min(1, len(axis_opts) - 1)]

    ui.label("Archive scatter").classes("text-subtitle2")
    ui.label("Green = feasible · Red = infeasible · Star = dominant archive member").classes("text-caption")

    with ui.row().classes("w-full gap-2 items-end"):
        x_sel = ui.select(axis_opts, label="X", value=session.forge_scatter_x).classes("flex-1")
        y_sel = ui.select(axis_opts, label="Y", value=session.forge_scatter_y).classes("flex-1")

        def _sync_axes() -> None:
            session.forge_scatter_x = str(x_sel.value)
            session.forge_scatter_y = str(y_sel.value)
            _render_view_body.refresh()

        x_sel.on("update:model-value", lambda: _sync_axes())
        y_sel.on("update:model-value", lambda: _sync_axes())

    _render_scatter(archive, session.forge_scatter_x, session.forge_scatter_y)

    ui.separator().classes("q-my-sm")
    rows = archive_table_rows(run_rep, limit=80)
    if rows:
        ui.label("Candidate table").classes("text-subtitle2")
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
                {"name": "dominant", "label": "Dom", "field": "dominant"},
            ],
            rows=rows,
            row_key="idx",
            pagination={"rowsPerPage": 12},
        ).classes("w-full")


def _render_scatter(archive: list, x_key: str, y_key: str) -> None:
    if not archive:
        ui.label("Empty archive.").classes("text-caption")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        ui.label("Plotly not available.").classes("text-orange")
        return

    xs, ys, colors, sizes, texts = [], [], [], [], []
    for i, a in enumerate(archive):
        if not isinstance(a, dict):
            continue
        xv = archive_point(a, x_key)
        yv = archive_point(a, y_key)
        if xv is None or yv is None:
            continue
        xs.append(float(xv))
        ys.append(float(yv))
        ok = bool(a.get("feasible", False))
        dom = bool(a.get("is_dominant", False))
        colors.append("#2e7d32" if ok else "#c62828")
        sizes.append(14 if dom else 8)
        texts.append(f"#{i} · {a.get('failure_mode') or 'OK'}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker=dict(color=colors, size=sizes, line=dict(width=1, color="#333")),
            text=texts,
            hovertemplate="%{text}<br>%{x}<br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(
        height=400,
        margin=dict(l=48, r=20, t=24, b=48),
        xaxis_title=x_key,
        yaxis_title=y_key,
        showlegend=False,
    )
    ui.plotly(fig).classes("w-full")


def _render_candidate_inspector(session: DesignSession, archive: list, intent: str) -> None:
    if not archive:
        empty_state("Archive is empty.", kind="info")
        return
    max_idx = max(len(archive) - 1, 0)
    idx = min(max(int(session.forge_inspect_idx or 0), 0), max_idx)
    session.forge_inspect_idx = idx

    ui.number(
        "Candidate index",
        value=idx,
        min=0,
        max=max_idx,
        step=1,
        on_change=lambda e: (
            setattr(session, "forge_inspect_idx", int(e.value or 0)),
            _render_view_body.refresh(),
        ),
    ).classes("w-48 q-mb-sm")

    cand = archive[idx]
    if not isinstance(cand, dict):
        return
    ui.label(f"Feasible: {bool(cand.get('feasible'))} · Score: {cand.get('_score')} · "
             f"Failure: {cand.get('failure_mode') or '-'}").classes("text-body2")

    instruments = enrich_candidate_instruments(cand, intent)
    if instruments.get("error"):
        ui.label(f"Instruments unavailable: {instruments['error']}").classes("text-orange")

    with ui.expansion("Closure console", icon="fact_check").classes("w-full"):
        cb = instruments.get("closure_bundle")
        render_json_blob(cb if isinstance(cb, dict) else {"note": "No closure bundle"})

    with ui.expansion("Margin budget", icon="account_balance").classes("w-full"):
        mb = instruments.get("margin_budget")
        render_json_blob(mb if isinstance(mb, (dict, list)) else {"note": "No margin budget"})

    with ui.expansion("Reality gates", icon="gavel").classes("w-full"):
        rg = instruments.get("reality_gates")
        render_json_blob(rg if isinstance(rg, (dict, list)) else {"note": "No gates"})

    with ui.expansion("Why-not report", icon="help_outline").classes("w-full"):
        wn = why_not_for_candidate(cand, intent)
        render_json_blob(wn if isinstance(wn, dict) else {"note": "Unavailable"})

    card_md = design_card_markdown(cand, intent)
    if card_md.strip():
        with ui.expansion("Design card (markdown)", icon="badge").classes("w-full"):
            ui.markdown(card_md)

    rp = instruments.get("report_pack")
    if isinstance(rp, dict):
        with ui.expansion("Report pack", icon="description").classes("w-full"):
            render_json_blob(rp)


def _render_resistance(session: DesignSession, run_rep: dict) -> None:
    atlas_rows = resistance_atlas_rows(run_rep)
    if atlas_rows:
        ui.label("Trace resistance atlas").classes("text-subtitle2")
        ui.table(
            columns=[
                {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                {"name": "count", "label": "Count", "field": "count"},
                {"name": "fraction", "label": "Share", "field": "fraction"},
            ],
            rows=atlas_rows,
            row_key="constraint",
        ).classes("w-full")

    conflict_rows = summarize_conflict_atlas(session.forge_conflict_atlas or {})
    if conflict_rows:
        ui.separator().classes("q-my-sm")
        ui.label("Conflict atlas (accumulated)").classes("text-subtitle2")
        ui.table(
            columns=[
                {"name": k, "label": k.replace("_", " ").title(), "field": k, "align": "left"}
                for k in conflict_rows[0].keys()
            ],
            rows=conflict_rows,
            row_key=list(conflict_rows[0].keys())[0] if conflict_rows else "constraint",
        ).classes("w-full")
    elif isinstance(run_rep.get("resistance_report"), dict):
        with ui.expansion("Resistance report (raw)", icon="description").classes("w-full"):
            render_json_blob(run_rep["resistance_report"])
    else:
        ui.label("No resistance report in this run.").classes("text-caption")


def _render_review_bench(
    session: DesignSession,
    run_rep: dict,
    archive: list,
    *,
    review_mode: bool,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Pin up to 5 archive rows for side-by-side comparison.").classes("text-caption q-mb-sm")
    bench = [i for i in (session.forge_review_bench or []) if isinstance(i, int) and 0 <= i < len(archive)][:5]
    session.forge_review_bench = bench

    with ui.row().classes("gap-2 items-center"):
        pick = ui.number("Pin index", value=0, min=0, max=max(len(archive) - 1, 0), step=1)

        def _pin() -> None:
            ix = int(pick.value or 0)
            pins = list(session.forge_review_bench or [])
            if ix not in pins:
                pins.append(ix)
            session.forge_review_bench = pins[-5:]
            _render_view_body.refresh()

        ui.button("Pin candidate", icon="push_pin", on_click=_pin).props("outline")

        def _clear() -> None:
            session.forge_review_bench = []
            _render_view_body.refresh()

        ui.button("Clear bench", icon="clear", on_click=_clear).props("flat")

    if not bench:
        empty_state("No pinned candidates — pin from the archive index.", kind="info")
        return

    rows = []
    for ix in bench:
        a = archive[ix]
        if not isinstance(a, dict):
            continue
        inp = a.get("inputs") or {}
        rows.append({
            "idx": ix,
            "feasible": bool(a.get("feasible")),
            "score": a.get("_score"),
            "R0_m": inp.get("R0_m"),
            "Bt_T": inp.get("Bt_T"),
            "Ip_MA": inp.get("Ip_MA"),
            "Paux_MW": inp.get("Paux_MW"),
            "failure": a.get("failure_mode") or "-",
        })

    ui.table(
        columns=[
            {"name": "idx", "label": "#", "field": "idx"},
            {"name": "feasible", "label": "OK", "field": "feasible"},
            {"name": "score", "label": "Score", "field": "score"},
            {"name": "R0_m", "label": "R0", "field": "R0_m"},
            {"name": "Bt_T", "label": "Bt", "field": "Bt_T"},
            {"name": "Ip_MA", "label": "Ip", "field": "Ip_MA"},
            {"name": "Paux_MW", "label": "Paux", "field": "Paux_MW"},
            {"name": "failure", "label": "Failure", "field": "failure", "align": "left"},
        ],
        rows=rows,
        row_key="idx",
    ).classes("w-full")

    if review_mode:
        ui.label("Review Mode: promotion disabled.").classes("text-orange q-mt-sm")
        return

    ui.separator().classes("q-my-sm")
    render_archive_handoffs(
        session,
        run_rep,
        review_mode=review_mode,
        on_complete=on_complete,
        default_row=int(bench[0]),
    )


def _render_ladder(session: DesignSession, archive: list) -> None:
    rows = ladder_histogram_rows(archive)
    if not rows:
        ui.label("Ladder histogram unavailable for this archive.").classes("text-caption")
        return
    ui.label("Score / regime ladder").classes("text-subtitle2")
    ui.table(
        columns=[
            {"name": "bucket", "label": "Bucket", "field": "bucket", "align": "left"},
            {"name": "count", "label": "Count", "field": "count"},
        ],
        rows=rows,
        row_key="bucket",
    ).classes("w-full")
