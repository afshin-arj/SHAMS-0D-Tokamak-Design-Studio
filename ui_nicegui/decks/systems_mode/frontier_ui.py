"""Frontier visualization — precheck / recovery / search traces with Plotly."""

from __future__ import annotations

import math

from nicegui import ui

from ui_nicegui.session import DesignSession

_Y_OPTS = [
    "Q_DT_eqv",
    "H98",
    "q95_proxy",
    "P_e_net_MW",
    "Pfus_total_MW",
    "V (hard violation)",
]
_X_OPTS = ["R0_m", "a_m", "Bt_T", "Ti_keV", "Paux_MW", "Ip_MA", "fG", "kappa"]


def render_frontier_panel(session: DesignSession) -> None:
    with ui.expansion("Frontier scatter", icon="scatter_plot", value=True).classes("w-full q-mt-sm"):
        src = ui.select(
            ["Precheck samples", "Seeded recovery trace", "Feasible search trace"],
            label="Source",
            value=session.systems_frontier_src,
            on_change=lambda e: (_set_src(session, str(e.value)), _frontier_view.refresh()),
        ).classes("w-48")
        x_key = ui.select(
            _X_OPTS,
            label="X variable",
            value=session.systems_frontier_x if session.systems_frontier_x in _X_OPTS else _X_OPTS[4],
            on_change=lambda e: (_set_x(session, str(e.value)), _frontier_view.refresh()),
        ).classes("w-36")
        y_key = ui.select(
            _Y_OPTS,
            label="Y metric",
            value=session.systems_frontier_y if session.systems_frontier_y in _Y_OPTS else _Y_OPTS[0],
            on_change=lambda e: (_set_y(session, str(e.value)), _frontier_view.refresh()),
        ).classes("w-36")
        _frontier_view(session, str(src.value), str(x_key.value), str(y_key.value))


def _set_src(session: DesignSession, v: str) -> None:
    session.systems_frontier_src = v


def _set_x(session: DesignSession, v: str) -> None:
    session.systems_frontier_x = v


def _set_y(session: DesignSession, v: str) -> None:
    session.systems_frontier_y = v


@ui.refreshable
def _frontier_view(session: DesignSession, src: str, x_key: str, y_key: str) -> None:
    pts = _collect_points(session, src, x_key, y_key)
    if not pts:
        ui.label("No points — run precheck, recovery, or search first.").classes("text-grey")
        return

    n_feas = sum(1 for p in pts if p[2])
    ui.label(f"Points: {len(pts)} | feasible: {n_feas}").classes("text-caption q-mb-xs")
    _render_plotly_scatter(pts, x_key, y_key)

    rows = [{"x": p[0], "y": p[1], "feasible": p[2]} for p in pts[:100]]
    with ui.expansion("Point table", icon="table_rows").classes("w-full"):
        ui.table(
            columns=[
                {"name": "x", "label": "X", "field": "x"},
                {"name": "y", "label": "Y", "field": "y"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
            ],
            rows=rows,
            row_key="x",
        ).classes("w-full")


def _render_plotly_scatter(pts: list[tuple[float, float, bool]], x_key: str, y_key: str) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        ui.label("Install plotly for scatter chart.").classes("text-caption text-grey")
        return

    feas = [(p[0], p[1]) for p in pts if p[2]]
    infeas = [(p[0], p[1]) for p in pts if not p[2]]
    fig = go.Figure()
    if infeas:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in infeas],
                y=[p[1] for p in infeas],
                mode="markers",
                name="Infeasible",
                marker=dict(color="rgba(160,160,160,0.35)", size=5),
            )
        )
    if feas:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in feas],
                y=[p[1] for p in feas],
                mode="markers",
                name="Feasible",
                marker=dict(color="#1976d2", size=7),
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


def _metric_from_outputs(outs: dict, y_key: str) -> float:
    """Prefer L0 keys; allow legacy aliases so frontier plots are not blank."""
    if y_key in outs and outs.get(y_key) is not None:
        return float(outs[y_key])
    aliases = {
        "q95_proxy": ("q95",),
        "q95": ("q95_proxy",),
        "Pfus_total_MW": ("P_fus_MW", "Pfus_MW"),
        "Pfus_DT_adj_MW": ("Pfus_total_MW",),
    }
    for alt in aliases.get(y_key, ()):
        if alt in outs and outs.get(alt) is not None:
            return float(outs[alt])
    return float("nan")


def _collect_points(session: DesignSession, src: str, x_key: str, y_key: str) -> list[tuple[float, float, bool]]:
    pts: list[tuple[float, float, bool]] = []
    if src == "Precheck samples":
        pre = session.last_precheck_report
        if pre is None:
            return pts
        samples = getattr(pre, "samples", None) or (pre.get("samples") if isinstance(pre, dict) else None) or []
        for sr in samples:
            try:
                sp = getattr(sr, "sample", None)
                xv = float(getattr(sp, "values", {}).get(x_key, float("nan")))
                if y_key == "V (hard violation)":
                    yv = float(getattr(sr, "violation_score", float("nan")))
                else:
                    outs = getattr(sr, "outputs", {}) or {}
                    yv = _metric_from_outputs(outs if isinstance(outs, dict) else {}, y_key)
                feas = len(getattr(sr, "hard_failed", []) or []) == 0
                if math.isfinite(xv) and math.isfinite(yv):
                    pts.append((xv, yv, feas))
            except Exception:
                continue
    elif src == "Seeded recovery trace":
        rep = session.systems_recovery_last or {}
        for t in rep.get("trace") or []:
            try:
                x = t.get("x") or {}
                xv = float(x.get(x_key, float("nan")))
                yv = float(t.get("V", float("nan")))
                if math.isfinite(xv) and math.isfinite(yv):
                    pts.append((xv, yv, bool(t.get("feasible"))))
            except Exception:
                continue
    else:
        rep = session.systems_feasible_search_last or {}
        for t in rep.get("trace") or []:
            try:
                x = t.get("x") or {}
                xv = float(x.get(x_key, float("nan")))
                if y_key == "V (hard violation)":
                    yv = float(t.get("V", float("nan")))
                else:
                    yv = _metric_from_outputs(t.get("metrics") or {}, y_key)
                if math.isfinite(xv) and math.isfinite(yv):
                    pts.append((xv, yv, bool(t.get("feasible"))))
            except Exception:
                continue
    return pts
