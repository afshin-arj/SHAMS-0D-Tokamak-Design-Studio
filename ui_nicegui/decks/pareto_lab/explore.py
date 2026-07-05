"""Pareto Lab — Explore Frontier tab (interactive plot + table)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.pareto_helpers import OBJ_CATALOG
from ui_nicegui.lib.pareto_interpret_helpers import enrich_pareto_front, failure_atlas_points, robust_filtered
from ui_nicegui.session import DesignSession


def render_explore_tab(
    session: DesignSession,
    pareto_last: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    pareto = pareto_last.get("pareto") or []
    feasible = pareto_last.get("feasible") or []
    objectives = pareto_last.get("objectives") or {}
    obj_keys = list(objectives.keys())
    all_samples = pareto_last.get("all") or []

    if not pareto and not feasible:
        ui.label("No feasible points — adjust bounds or intent on **Setup & Run**.").classes("text-orange")
        return

    plot_keys = obj_keys + [k for k in ("R0_m", "Bt_T", "Ip_MA", "fG") if k not in obj_keys]
    if not plot_keys:
        plot_keys = ["R0_m", "P_e_net_MW"]

    if session.pareto_plot_x not in plot_keys:
        session.pareto_plot_x = obj_keys[0] if obj_keys else plot_keys[0]
    if session.pareto_plot_y not in plot_keys:
        session.pareto_plot_y = obj_keys[1] if len(obj_keys) > 1 else plot_keys[min(1, len(plot_keys) - 1)]

    ui.label("Frontier plot").classes("text-subtitle2")
    ui.label("Gray = infeasible shadow · Color = dominant constraint on Pareto points").classes("text-caption")

    with ui.row().classes("w-full gap-2 items-end"):
        x_sel = ui.select(plot_keys, label="X axis", value=session.pareto_plot_x).classes("flex-1")
        y_sel = ui.select(plot_keys, label="Y axis", value=session.pareto_plot_y).classes("flex-1")
        color_opts = ["dominant_constraint", "geography", "segment_id", "confidence", "(none)"] + obj_keys
        c_val = session.pareto_plot_color if session.pareto_plot_color in color_opts else "dominant_constraint"
        c_sel = ui.select(color_opts, label="Color", value=c_val).classes("flex-1")
        robust_sw = ui.switch(
            "Robust overlay only",
            value=session.pareto_robust_only,
        ).classes("flex-none")
        fail_sw = ui.switch("Show failure atlas", value=session.pareto_show_failures).classes("flex-none")

    def _sync() -> None:
        session.pareto_plot_x = str(x_sel.value)
        session.pareto_plot_y = str(y_sel.value)
        session.pareto_plot_color = str(c_sel.value)
        session.pareto_robust_only = bool(robust_sw.value)
        session.pareto_show_failures = bool(fail_sw.value)
        if on_update:
            on_update()

    for w in (x_sel, y_sel, c_sel):
        w.on("update:model-value", lambda: _sync())
    robust_sw.on("update:model-value", lambda: _sync())
    fail_sw.on("update:model-value", lambda: _sync())

    x_key, y_key = session.pareto_plot_x, session.pareto_plot_y
    thr = float(pareto_last.get("robust_margin_thr") or session.pareto_robust_margin_thr or 0.1)
    plot_pareto = robust_filtered(pareto, thr) if session.pareto_robust_only else list(pareto)
    enriched = enrich_pareto_front(
        plot_pareto, feasible, x_key=x_key, y_key=y_key, robust_margin_thr=thr,
    )
    pareto_last["pareto_enriched"] = enriched
    color_key = str(session.pareto_plot_color)
    if color_key in ("geography", "segment_id", "confidence"):
        plot_src = enriched
    else:
        plot_src = plot_pareto
    _render_plot(
        plot_src if color_key != "(none)" else plot_pareto,
        x_key,
        y_key,
        color_key,
        failure_pts=failure_atlas_points(all_samples, x_key, y_key) if session.pareto_show_failures else [],
    )

    ui.separator().classes("q-my-sm")
    _render_table(enriched or plot_pareto or pareto, obj_keys)


def _render_plot(
    pareto: list[dict],
    x_key: str,
    y_key: str,
    color_key: str,
    *,
    failure_pts: list[dict],
) -> None:
    if not pareto and not failure_pts:
        ui.label("Nothing to plot.").classes("text-caption")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        ui.label("Plotly not available.").classes("text-orange")
        return

    fig = go.Figure()
    if failure_pts:
        fig.add_trace(
            go.Scatter(
                x=[p.get(x_key) for p in failure_pts],
                y=[p.get(y_key) for p in failure_pts],
                mode="markers",
                name="Infeasible",
                marker=dict(color="rgba(160,160,160,0.35)", size=5),
                hovertext=[p.get("first_failure") for p in failure_pts],
            )
        )
    if pareto:
        colors = None
        if color_key and color_key != "(none)":
            colors = [str(p.get(color_key) or "") for p in pareto]
        fig.add_trace(
            go.Scatter(
                x=[p.get(x_key) for p in pareto],
                y=[p.get(y_key) for p in pareto],
                mode="markers",
                name="Pareto",
                marker=dict(size=9, color=colors if colors and any(colors) else "#1976d2"),
                text=[f"dom: {p.get('dominant_constraint')}" for p in pareto],
            )
        )
    xu = OBJ_CATALOG.get(x_key, {}).get("units", "-")
    yu = OBJ_CATALOG.get(y_key, {}).get("units", "-")
    fig.update_layout(
        height=420,
        margin=dict(l=48, r=20, t=36, b=48),
        xaxis_title=f"{x_key} [{xu}]",
        yaxis_title=f"{y_key} [{yu}]",
        legend=dict(orientation="h"),
    )
    ui.plotly(fig).classes("w-full")


def _render_table(pareto: list[dict], obj_keys: list[str]) -> None:
    cols = ["intent", "dominant_constraint", "min_constraint_margin", "geography", "freedom_left", "segment_id", "confidence"] + obj_keys[:8]
    rows = []
    for i, p in enumerate(pareto[:80]):
        row = {"idx": i}
        for c in cols:
            if c in p:
                row[c] = p[c]
        rows.append(row)
    if not rows:
        return
    ui.label(f"Pareto table ({len(pareto)} points, showing {len(rows)})").classes("text-subtitle2")
    ui.table(
        columns=[{"name": k, "label": k, "field": k, "align": "left"} for k in ["idx"] + [c for c in cols if c in rows[0]]],
        rows=rows,
        row_key="idx",
        pagination={"rowsPerPage": 15},
    ).classes("w-full")
