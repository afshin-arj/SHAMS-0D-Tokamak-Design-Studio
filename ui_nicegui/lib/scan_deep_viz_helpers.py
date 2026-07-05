"""Scan Lab advanced landscape visualizations — iso-manifolds, vector field, coupling, intent-split."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ui_nicegui.lib.scan_workbench_helpers import build_point_grid, cell_intent_state


def constraint_names_from_report(rep: dict) -> List[str]:
    names: set[str] = set()
    for p in rep.get("points") or []:
        if not isinstance(p, dict):
            continue
        mh = p.get("margins_hard")
        if isinstance(mh, dict):
            names.update(str(k) for k in mh.keys())
    return sorted(names)


def iso_margin_matrix(rep: dict, constraint: str) -> Tuple[List[List[float]], List[List[float]]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    feas: List[List[float]] = []
    margins: List[List[float]] = []
    import math

    for j in range(len(y_vals)):
        frow: List[float] = []
        mrow: List[float] = []
        for i in range(len(x_vals)):
            cell = grid.get((i, j), {})
            s = cell_intent_state(grid, "Reactor", i, j)
            frow.append(1.0 if bool(s.get("blocking_feasible")) else 0.0)
            mh = cell.get("margins_hard") if isinstance(cell.get("margins_hard"), dict) else {}
            try:
                mrow.append(float(mh.get(str(constraint))))
            except (TypeError, ValueError):
                mrow.append(float("nan"))
        feas.append(frow)
        margins.append(mrow)
    return feas, margins


def plotly_iso_contour_figure(rep: dict, intent: str, constraint: str):
    import plotly.graph_objects as go

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    _, margins = iso_margin_matrix(rep, constraint)
    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=[[1.0 if v > 0.5 else 0.0 for v in row] for row in _feas_matrix(rep, intent)],
            colorscale=[[0, "#ffcdd2"], [1, "#c8e6c9"]],
            zmin=0,
            zmax=1,
            showscale=False,
            name="Feasible",
        )
    )
    fig.add_trace(
        go.Contour(
            x=x_vals,
            y=y_vals,
            z=margins,
            contours={"start": 0, "end": 0, "size": 0, "coloring": "lines"},
            line={"color": "black", "width": 2},
            showscale=False,
            name=f"{constraint} margin=0",
        )
    )
    fig.update_layout(
        title=f"Iso-contour: {constraint} margin = 0 — {intent}",
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def _feas_matrix(rep: dict, intent: str) -> List[List[float]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    z: List[List[float]] = []
    for j in range(len(y_vals)):
        row: List[float] = []
        for i in range(len(x_vals)):
            s = cell_intent_state(grid, intent, i, j)
            row.append(1.0 if bool(s.get("blocking_feasible")) else 0.0)
        z.append(row)
    return z


def margin_gradient_field(rep: dict, intent: str) -> Tuple[List[List[float]], List[List[float]], List[List[float]]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    nx, ny = len(x_vals), len(y_vals)
    margin: List[List[float]] = []
    for j in range(ny):
        row: List[float] = []
        for i in range(nx):
            s = cell_intent_state(grid, intent, i, j)
            try:
                row.append(float(s.get("min_blocking_margin")))
            except (TypeError, ValueError):
                row.append(float("nan"))
        margin.append(row)

    gx: List[List[float]] = [[0.0] * nx for _ in range(ny)]
    gy: List[List[float]] = [[0.0] * nx for _ in range(ny)]
    for j in range(ny):
        for i in range(nx):
            if i > 0 and i < nx - 1:
                gx[j][i] = (margin[j][i + 1] - margin[j][i - 1]) / max(
                    abs(float(x_vals[i + 1]) - float(x_vals[i - 1])), 1e-12
                )
            if j > 0 and j < ny - 1:
                gy[j][i] = (margin[j + 1][i] - margin[j - 1][i]) / max(
                    abs(float(y_vals[j + 1]) - float(y_vals[j - 1])), 1e-12
                )
    return margin, gx, gy


def plotly_margin_vector_figure(rep: dict, intent: str):
    import plotly.graph_objects as go

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    if len(x_vals) < 3 or len(y_vals) < 3:
        raise ValueError("Vector field requires Nx,Ny ≥ 3")
    margin, gx, gy = margin_gradient_field(rep, intent)
    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=_feas_matrix(rep, intent),
            colorscale=[[0, "#ffcdd2"], [1, "#c8e6c9"]],
            zmin=0,
            zmax=1,
            showscale=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[x_vals[i] for j in range(len(y_vals)) for i in range(len(x_vals))],
            y=[y_vals[j] for j in range(len(y_vals)) for i in range(len(x_vals))],
            mode="markers",
            marker={"size": 1, "opacity": 0},
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Cone(
            x=[x_vals[i] for j in range(1, len(y_vals) - 1) for i in range(1, len(x_vals) - 1)],
            y=[y_vals[j] for j in range(1, len(y_vals) - 1) for i in range(1, len(x_vals) - 1)],
            u=[gx[j][i] for j in range(1, len(y_vals) - 1) for i in range(1, len(x_vals) - 1)],
            v=[gy[j][i] for j in range(1, len(y_vals) - 1) for i in range(1, len(x_vals) - 1)],
            w=[0.0] * max(1, (len(y_vals) - 2) * max(0, len(x_vals) - 2)),
            sizemode="absolute",
            sizeref=0.5,
            anchor="tail",
            colorscale="Blues",
            showscale=False,
        )
    )
    fig.update_layout(
        title=f"Margin gradient field — {intent}",
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def coupling_matrix_rows(rep: dict, intent: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    inter = rep.get("interaction") if isinstance(rep.get("interaction"), dict) else {}
    intents_map = inter.get("intents") if isinstance(inter.get("intents"), dict) else {}
    blob = intents_map.get(str(intent)) if isinstance(intents_map, dict) else {}
    names = blob.get("names") if isinstance(blob, dict) else None
    mat = blob.get("before_counts") if isinstance(blob, dict) else None
    if not isinstance(names, list) or not isinstance(mat, dict):
        return [], []
    rows: List[Dict[str, Any]] = []
    for a in names:
        row: Dict[str, Any] = {"from": str(a)}
        for b in names:
            try:
                row[str(b)] = int((mat.get(str(a)) or {}).get(str(b), 0))
            except (TypeError, ValueError):
                row[str(b)] = 0
        rows.append(row)
    return [str(n) for n in names], rows


def robustness_label_counts(rep: dict, intent: str) -> Dict[str, int]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    counts: Dict[str, int] = {}
    for j in range(len(y_vals)):
        for i in range(len(x_vals)):
            s = cell_intent_state(grid, intent, i, j)
            lab = str(s.get("robustness") or "Unknown")
            counts[lab] = counts.get(lab, 0) + 1
    return counts


def intent_split_overlay_figure(rep: dict):
    """Hatched overlay: Research-feasible but Reactor-infeasible."""
    import plotly.graph_objects as go
    from ui_nicegui.lib.scan_workbench_helpers import plotly_dominance_figure

    intents = list(rep.get("intents") or [])
    if "Research" not in intents or "Reactor" not in intents:
        raise ValueError("Both Research and Reactor intents required")
    base = plotly_dominance_figure(rep, "Reactor")
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    mask: List[List[float]] = []
    for j in range(len(y_vals)):
        row: List[float] = []
        for i in range(len(x_vals)):
            r_ok = bool(cell_intent_state(grid, "Research", i, j).get("blocking_feasible"))
            x_ok = bool(cell_intent_state(grid, "Reactor", i, j).get("blocking_feasible"))
            row.append(1.0 if (r_ok and not x_ok) else 0.0)
        mask.append(row)
    fig = go.Figure(data=base.data)
    fig.add_trace(
        go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=mask,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(255,152,0,0.45)"]],
            zmin=0,
            zmax=1,
            showscale=False,
            name="Research-only feasible",
        )
    )
    fig.update_layout(
        title="Intent-split overlay (orange = Research-feasible, Reactor-infeasible)",
        height=420,
    )
    return fig


def intent_split_png_bytes(rep: dict) -> Optional[bytes]:
    try:
        import io

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        x_vals = rep.get("x_vals") or []
        y_vals = rep.get("y_vals") or []
        grid = build_point_grid(rep)
        only_r = np.zeros((len(y_vals), len(x_vals)))
        for j in range(len(y_vals)):
            for i in range(len(x_vals)):
                r_ok = bool(cell_intent_state(grid, "Research", i, j).get("blocking_feasible"))
                x_ok = bool(cell_intent_state(grid, "Reactor", i, j).get("blocking_feasible"))
                only_r[j, i] = 1.0 if (r_ok and not x_ok) else 0.0
        if not only_r.any():
            return None
        fig, ax = plt.subplots(figsize=(7.6, 4.4))
        ax.imshow(only_r, origin="lower", aspect="auto", cmap="Oranges", alpha=0.7)
        ax.set_title("Intent-split (Research-only feasible)")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        return None
