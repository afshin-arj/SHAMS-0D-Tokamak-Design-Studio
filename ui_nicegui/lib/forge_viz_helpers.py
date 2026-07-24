"""Forge visualization helpers — local cartography heatmap, trace charts."""
from __future__ import annotations

from typing import List, Optional


def local_cartography_figure(rows: list) -> Optional[object]:
    """Plotly heatmap of blocking-OK (1) vs fail (0) from cartography grid rows.

    Colors are blue/amber (Scan Lab cartography posture parity) — never PD hero
    green/red FEASIBLE chrome.
    """
    if not rows:
        return None
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    xs = sorted({float(r["x"]) for r in rows if r.get("x") is not None})
    ys = sorted({float(r["y"]) for r in rows if r.get("y") is not None})
    if len(xs) < 2 or len(ys) < 2:
        return None

    grid = [[None for _ in xs] for _ in ys]
    for r in rows:
        try:
            xi = xs.index(float(r["x"]))
            yi = ys.index(float(r["y"]))
            grid[yi][xi] = 1.0 if r.get("feasible") else 0.0
        except (ValueError, KeyError, TypeError):
            continue

    fig = go.Figure(
        data=go.Heatmap(
            z=grid,
            x=xs,
            y=ys,
            colorscale=[[0, "#ef6c00"], [1, "#1565c0"]],
            zmin=0,
            zmax=1,
            colorbar=dict(title="Blocking-OK<br>(intent)"),
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=48, r=20, t=36, b=48),
        xaxis_title="x",
        yaxis_title="y",
        title="Local cartography (intent blocking — not PD hero verdict)",
    )
    return fig


def trace_score_figure(trace: list) -> Optional[object]:
    if not trace:
        return None
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    scores = [t.get("_score") for t in trace if t.get("_score") is not None]
    if not scores:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=scores, mode="lines+markers", name="Score"))
    fig.update_layout(
        height=320,
        margin=dict(l=48, r=20, t=24, b=48),
        xaxis_title="Evaluation index",
        yaxis_title="Score",
        title="Trace score progression",
    )
    return fig
