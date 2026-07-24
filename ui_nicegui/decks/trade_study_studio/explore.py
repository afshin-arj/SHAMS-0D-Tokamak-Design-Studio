"""Trade Study — Explore Results tab."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.plant_kpi_honesty_ui import (
    allow_infeasible_scatter_point,
    scatter_physkpi_caption,
    watermark_trade_study_table_rows,
)
from ui_nicegui.session import DesignSession


def render_explore_tab(
    session: DesignSession,
    rep: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    pareto = rep.get("pareto") or []
    feasible = rep.get("feasible") or []
    records = rep.get("records") or []
    objectives = (rep.get("meta") or {}).get("objectives") or []

    if not records:
        ui.label("No samples in this run.").classes("text-orange")
        return

    plot_keys = list(objectives)
    for k in ("R0_m", "Bt_T", "Ip_MA", "fG", "P_e_net_MW"):
        if k not in plot_keys:
            plot_keys.append(k)

    if session.trade_plot_x not in plot_keys:
        session.trade_plot_x = objectives[0] if objectives else plot_keys[0]
    if session.trade_plot_y not in plot_keys:
        session.trade_plot_y = objectives[1] if len(objectives) > 1 else plot_keys[min(1, len(plot_keys) - 1)]

    ui.label("blocking-OK Pareto plot (intent-gate — not L0 FEASIBLE)").classes("text-subtitle2")
    with ui.row().classes("w-full gap-2 items-end"):
        x_sel = ui.select(plot_keys, label="X axis", value=session.trade_plot_x).classes("flex-1")
        y_sel = ui.select(plot_keys, label="Y axis", value=session.trade_plot_y).classes("flex-1")
        color_opts = ["design_family", "dominant_constraint", "(none)"] + objectives
        c_val = session.trade_plot_color if session.trade_plot_color in color_opts else "design_family"
        c_sel = ui.select(color_opts, label="Color", value=c_val).classes("flex-1")
        fail_sw = ui.switch("Show blocking-fail shadow", value=session.trade_show_failures).classes("flex-none")

    def _sync() -> None:
        session.trade_plot_x = str(x_sel.value)
        session.trade_plot_y = str(y_sel.value)
        session.trade_plot_color = str(c_sel.value)
        session.trade_show_failures = bool(fail_sw.value)
        if on_update:
            on_update()

    for w in (x_sel, y_sel, c_sel):
        w.on("update:model-value", lambda: _sync())
    fail_sw.on("update:model-value", lambda: _sync())

    if pareto and len(objectives) >= 1:
        _render_plot(
            pareto,
            session.trade_plot_x,
            session.trade_plot_y,
            session.trade_plot_color,
            infeasible=_infeasible_shadow(records, session.trade_plot_x, session.trade_plot_y)
            if session.trade_show_failures
            else [],
            show_infeasible=bool(session.trade_show_failures),
        )
    elif not pareto:
        ui.label("No Pareto front — insufficient blocking-OK variation or single objective.").classes("text-orange")

    ui.separator().classes("q-my-sm")
    _render_sample_table("blocking-OK Pareto subset", pareto[:80], objectives)
    if feasible and len(feasible) != len(pareto):
        _render_sample_table("All blocking-OK samples", feasible[:80], objectives)


def _infeasible_shadow(records: list, x_key: str, y_key: str) -> list[dict]:
    """Geometry/margin shadows only — omit when axes are claim KPIs (PHYS-KPI-001)."""
    if not allow_infeasible_scatter_point(x_key=x_key, y_key=y_key):
        return []
    out = []
    for r in records:
        if r.get("is_feasible"):
            continue
        if r.get(x_key) is None or r.get(y_key) is None:
            continue
        out.append(r)
    return out[:2000]


def _render_plot(
    pareto: list[dict],
    x_key: str,
    y_key: str,
    color_key: str,
    *,
    infeasible: list[dict],
    show_infeasible: bool = False,
) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        return
    caption = scatter_physkpi_caption(x_key, y_key, show_infeasible=show_infeasible)
    if caption:
        ui.label(caption).classes("text-caption text-orange q-mb-xs")
    fig = go.Figure()
    if infeasible:
        fig.add_trace(
            go.Scatter(
                x=[p.get(x_key) for p in infeasible],
                y=[p.get(y_key) for p in infeasible],
                mode="markers",
                name="hard-fail (non-claim axes)",
                marker=dict(color="rgba(160,160,160,0.3)", size=4),
            )
        )
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
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=48, r=20, t=36, b=48),
        xaxis_title=x_key,
        yaxis_title=y_key,
        legend=dict(orientation="h"),
    )
    ui.plotly(fig).classes("w-full")


def _render_sample_table(title: str, rows: list[dict], objectives: list[str]) -> None:
    if not rows:
        return
    cols = ["i", "is_feasible", "dominant_constraint", "min_margin_frac", "design_family"]
    cols += [c for c in objectives if c in rows[0]][:4]
    table_rows = watermark_trade_study_table_rows(rows, cols)
    ui.label(title).classes("text-subtitle2")
    ui.table(
        columns=[{"name": k, "label": k, "field": k, "align": "left"} for k in cols if table_rows and k in table_rows[0]],
        rows=table_rows,
        row_key="i",
        pagination={"rowsPerPage": 15},
    ).classes("w-full")
