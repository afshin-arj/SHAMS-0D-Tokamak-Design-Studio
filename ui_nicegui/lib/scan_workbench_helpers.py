"""Scan Lab workbench helpers — dominance maps, probe, causality, families, atlas."""
from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional, Tuple

SCAN_WB_VIEWS = [
    "Dominance (blocking)",
    "Feasibility (blocking)",
    "Robustness (proxy)",
    "Operating contours (outputs)",
]


def build_point_grid(rep: dict) -> Dict[Tuple[int, int], dict]:
    pts = rep.get("points") or []
    grid: Dict[Tuple[int, int], dict] = {}
    for p in pts:
        if not isinstance(p, dict) or "i" not in p or "j" not in p:
            continue
        grid[(int(p["i"]), int(p["j"]))] = p
    return grid


def cell_intent_state(grid: Dict[Tuple[int, int], dict], intent: str, i: int, j: int) -> dict:
    cell = grid.get((int(i), int(j)), {})
    if not isinstance(cell, dict):
        return {}
    intent_map = cell.get("intent") or {}
    if not isinstance(intent_map, dict):
        return {}
    state = intent_map.get(str(intent)) or {}
    return state if isinstance(state, dict) else {}


def dominance_labels(rep: dict, intent: str) -> List[str]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    labels: set[str] = set()
    for j in range(len(y_vals)):
        for i in range(len(x_vals)):
            s = cell_intent_state(grid, intent, i, j)
            if bool(s.get("blocking_feasible")):
                labels.add("PASS")
            else:
                labels.add(str(s.get("dominant_blocking") or "FAIL (unknown)"))
    lab = sorted(labels)
    if "PASS" in lab:
        lab = ["PASS"] + [x for x in lab if x != "PASS"]
    return lab


def _dominance_matrix(rep: dict, intent: str) -> Tuple[List[List[str]], List[str]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    dom: List[List[str]] = []
    for j in range(len(y_vals)):
        row: List[str] = []
        for i in range(len(x_vals)):
            s = cell_intent_state(grid, intent, i, j)
            if bool(s.get("blocking_feasible")):
                row.append("PASS")
            else:
                row.append(str(s.get("dominant_blocking") or "FAIL (unknown)"))
        dom.append(row)
    labels = dominance_labels(rep, intent)
    return dom, labels


def _feasibility_matrix(rep: dict, intent: str) -> List[List[float]]:
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


def _robustness_matrix(rep: dict, intent: str) -> List[List[float]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    z: List[List[float]] = []
    for j in range(len(y_vals)):
        row: List[float] = []
        for i in range(len(x_vals)):
            s = cell_intent_state(grid, intent, i, j)
            try:
                row.append(float(s.get("local_p_feasible")))
            except (TypeError, ValueError):
                row.append(float("nan"))
        z.append(row)
    return z


def contour_field_keys(rep: dict) -> List[str]:
    fc = rep.get("field_cube") if isinstance(rep, dict) else None
    if isinstance(fc, dict):
        vars_map = fc.get("vars") or {}
        if isinstance(vars_map, dict) and vars_map:
            return sorted(str(k) for k in vars_map.keys())
    return []


def _contour_matrix(rep: dict, field: str) -> List[List[float]]:
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)
    fc = rep.get("field_cube") if isinstance(rep, dict) else None
    arr = None
    if isinstance(fc, dict):
        vars_map = fc.get("vars") or {}
        if isinstance(vars_map, dict):
            arr = vars_map.get(str(field))
    if isinstance(arr, list):
        try:
            import numpy as np

            return np.array(arr, dtype=float).tolist()
        except Exception:
            pass
    z: List[List[float]] = []
    for j in range(len(y_vals)):
        row: List[float] = []
        for i in range(len(x_vals)):
            cell = grid.get((i, j), {})
            outs = cell.get("outputs") if isinstance(cell, dict) else None
            val = float("nan")
            if isinstance(outs, dict) and field in outs:
                try:
                    val = float(outs.get(field))
                except (TypeError, ValueError):
                    val = float("nan")
            row.append(val)
        z.append(row)
    return z


def plotly_dominance_figure(rep: dict, intent: str):
    import plotly.graph_objects as go

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    dom, labels = _dominance_matrix(rep, intent)
    if not labels:
        labels = ["PASS"]
    lut = {lab: k for k, lab in enumerate(labels)}
    z = [[lut.get(str(row[i]), 0) for i in range(len(row))] for row in dom]
    try:
        from tools.scan_visual_identity import build_palette

        palette = build_palette(labels)
    except Exception:
        palette = ["#E0E0E0", "#4C78A8", "#F58518", "#54A24B", "#E45756"]
    if labels and labels[0] == "PASS":
        palette = list(palette)
        palette[0] = "#E0E0E0"
    n = max(len(labels), 1)
    colorscale = [[i / max(n - 1, 1), palette[i % len(palette)]] for i in range(n)]
    fig = go.Figure(
        data=go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=z,
            colorscale=colorscale,
            zmin=-0.5,
            zmax=n - 0.5,
            colorbar={"title": "Dominant", "tickvals": list(range(n)), "ticktext": labels},
        )
    )
    fig.update_layout(
        title=f"Dominant blocking constraint — {intent}",
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def plotly_feasibility_figure(rep: dict, intent: str):
    import plotly.graph_objects as go

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    z = _feasibility_matrix(rep, intent)
    fig = go.Figure(
        data=go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=z,
            colorscale=[[0, "#ef5350"], [1, "#66bb6a"]],
            zmin=0,
            zmax=1,
            colorbar={"title": "Feasible"},
        )
    )
    fig.update_layout(
        title=f"Blocking feasibility — {intent}",
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def plotly_robustness_figure(rep: dict, intent: str):
    import plotly.graph_objects as go

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    z = _robustness_matrix(rep, intent)
    fig = go.Figure(data=go.Heatmap(x=x_vals, y=y_vals, z=z, colorbar={"title": "p_feasible"}))
    fig.update_layout(
        title=f"Robustness proxy (local p-feasible) — {intent}",
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def plotly_contour_figure(rep: dict, intent: str, field: str):
    import plotly.graph_objects as go

    from ui_nicegui.lib.plant_kpi_honesty_ui import is_claim_kpi_key

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    z = _contour_matrix(rep, field)
    claim = is_claim_kpi_key(str(field))
    if claim:
        # PHYS-KPI-001: never paint claim KPI heatmaps on blocking-infeasible cells.
        grid = build_point_grid(rep)
        masked: List[List[float]] = []
        for j in range(len(y_vals)):
            row: List[float] = []
            for i in range(len(x_vals)):
                s = cell_intent_state(grid, intent, i, j)
                if not bool(s.get("blocking_feasible")):
                    row.append(float("nan"))
                else:
                    try:
                        row.append(float(z[j][i]))
                    except (IndexError, TypeError, ValueError):
                        row.append(float("nan"))
            masked.append(row)
        z = masked
        title = f"Operating contour: {field} (feasible cells) — INFEASIBLE = diagnostic blank"
        cbar = f"{field} (claim)"
    else:
        title = f"Operating contour: {field} — context {intent}"
        cbar = field
    fig = go.Figure(data=go.Heatmap(x=x_vals, y=y_vals, z=z, colorbar={"title": cbar}))
    fig.update_layout(
        title=title,
        xaxis_title=str(rep.get("x_key") or "x"),
        yaxis_title=str(rep.get("y_key") or "y"),
        height=420,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    return fig


def plotly_figure_for_view(rep: dict, intent: str, view: str, *, out_key: Optional[str] = None):
    v = str(view or "")
    if v.startswith("Dominance"):
        return plotly_dominance_figure(rep, intent)
    if v.startswith("Feasibility"):
        return plotly_feasibility_figure(rep, intent)
    if v.startswith("Operating") and out_key:
        return plotly_contour_figure(rep, intent, out_key)
    return plotly_robustness_figure(rep, intent)


def dominance_map_png_bytes(rep: dict, intent: str) -> bytes:
    """Matplotlib PNG for atlas PDF export (matches Streamlit workbench)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    dom, labels = _dominance_matrix(rep, intent)
    lut = {lab: k for k, lab in enumerate(labels)}
    z = np.vectorize(lambda s: lut.get(str(s), 0))(np.array(dom, dtype=object))
    try:
        from tools.scan_visual_identity import build_palette

        palette = build_palette(labels)
    except Exception:
        palette = ["#E0E0E0", "#4C78A8", "#F58518", "#54A24B", "#E45756"]
    if labels and labels[0] == "PASS":
        palette = list(palette)
        palette[0] = "#E0E0E0"
    cmap = ListedColormap(palette[: max(len(labels), 1)])
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.imshow(z, origin="lower", aspect="auto", cmap=cmap, vmin=-0.5, vmax=max(len(labels) - 1, 0.5))
    ax.set_xlabel(str(rep.get("x_key") or "x"))
    ax.set_ylabel(str(rep.get("y_key") or "y"))
    ax.set_title(f"Dominant blocking constraint — {intent}")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def build_atlas_pdf_bytes(rep: dict, intents: List[str], *, title: str = "SHAMS — Scan Lab Atlas") -> bytes:
    try:
        from tools.scan_next_tier import build_scan_atlas_pdf_bytes
    except ImportError as exc:
        raise RuntimeError("Atlas export unavailable (scan_next_tier import failed)") from exc

    pages = []
    for it in intents:
        pages.append(
            {
                "report": rep,
                "intent": str(it),
                "map_png": dominance_map_png_bytes(rep, str(it)),
                "page_title": f"{title} — {it}",
            }
        )
    return build_scan_atlas_pdf_bytes(pages=pages, title=title)


def probe_cell_summary(grid: Dict[Tuple[int, int], dict], rep: dict, intent: str, i: int, j: int) -> dict:
    cell = grid.get((int(i), int(j)), {})
    if not isinstance(cell, dict):
        return {}
    s = cell_intent_state(grid, intent, i, j)
    mh = cell.get("margins_hard") if isinstance(cell.get("margins_hard"), dict) else {}
    margin_rows = []
    if isinstance(mh, dict):
        for k, v in mh.items():
            try:
                margin_rows.append({"constraint": str(k), "margin_frac": float(v)})
            except (TypeError, ValueError):
                pass
        margin_rows.sort(key=lambda r: r["margin_frac"])
    outs = cell.get("outputs") if isinstance(cell.get("outputs"), dict) else {}
    perf = {}
    # Prefer L0 keys; keep legacy aliases only as fallback fill.
    key_chain = (
        ("Q_DT_eqv", ("Q_DT_eqv", "Q")),
        ("H98", ("H98", "H_IPB98y2", "H98y2", "H_IPB98")),
        ("Pfus_total_MW", ("Pfus_total_MW", "P_fus_MW", "Pfus_MW")),
        ("Pfus_DT_adj_MW", ("Pfus_DT_adj_MW",)),
        ("P_e_net_MW", ("P_e_net_MW", "P_net_e_MW", "Pe_net_MW", "P_net_MW", "Pnet_MWe")),
        ("tauE_eff_s", ("tauE_eff_s", "tau_E_s", "tauE_s")),
        ("q95_proxy", ("q95_proxy", "q95")),
        ("q_div_MW_m2", ("q_div_MW_m2",)),
        ("beta_N", ("beta_N", "betaN_proxy", "betaN")),
    )
    for label, aliases in key_chain:
        for k in aliases:
            if k in outs and outs[k] is not None:
                perf[label] = outs[k]
                break
    from ui_nicegui.lib.scan_v396_display import extract_v396_transport

    v396 = extract_v396_transport(outs)
    return {
        "x": cell.get("x"),
        "y": cell.get("y"),
        "i": int(i),
        "j": int(j),
        "intent": str(intent),
        "blocking_feasible": bool(s.get("blocking_feasible")),
        "dominant_blocking": s.get("dominant_blocking"),
        "min_blocking_margin": s.get("min_blocking_margin"),
        "robustness": s.get("robustness"),
        "local_p_feasible": s.get("local_p_feasible"),
        "failed_blocking": list(s.get("failed_blocking") or [])[:15],
        "margin_rows": margin_rows[:25],
        "failure_order": list(cell.get("failure_order_any") or [])[:15],
        "performance": perf,
        "v396": v396,
    }


def probe_promote_inputs(rep: dict, cell: dict) -> dict:
    base = rep.get("base_inputs") if isinstance(rep.get("base_inputs"), dict) else {}
    cand = dict(base)
    cand.update(_cell_xy_overrides(rep, cell))
    return cand


def _cell_xy_overrides(rep: dict, cell: dict) -> dict:
    x_key = str(rep.get("x_key") or "")
    y_key = str(rep.get("y_key") or "")
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    x_raw = cell.get("x")
    y_raw = cell.get("y")
    if x_raw is None and x_key:
        try:
            x_raw = x_vals[int(cell.get("i", 0))]
        except (IndexError, TypeError, ValueError):
            x_raw = None
    if y_raw is None and y_key:
        try:
            y_raw = y_vals[int(cell.get("j", 0))]
        except (IndexError, TypeError, ValueError):
            y_raw = None
    overrides: dict = {}
    if x_key and x_raw is not None:
        overrides[x_key] = float(x_raw)
    if y_key and y_raw is not None:
        overrides[y_key] = float(y_raw)
    return overrides


def run_causality_trace(
    base,
    rep: dict,
    *,
    intent: str,
    i: int,
    j: int,
    rel_step: float = 0.01,
) -> dict:
    try:
        from tools.scan_insights import build_causality_trace
    except ImportError as exc:
        raise RuntimeError("Causality engine unavailable") from exc

    grid = build_point_grid(rep)
    cell = grid.get((int(i), int(j)), {})
    s = cell_intent_state(grid, intent, i, j)
    domc = str(s.get("dominant_blocking") or "").strip()
    if not domc or domc.upper() == "PASS":
        return {"status": "skipped", "reason": "Cell is blocking-feasible; pick a failing cell."}

    x_key = str(rep.get("x_key") or "")
    y_key = str(rep.get("y_key") or "")
    point_overrides = _cell_xy_overrides(rep, cell)

    knobs = [x_key, y_key, "R0_m", "Bt_T", "Ip_MA", "fG", "Paux_MW", "a_m"]
    knobs = list(dict.fromkeys(k for k in knobs if k and hasattr(base, k)))

    try:
        from ui_nicegui.evaluate import ui_evaluator
    except ImportError:
        from ui_nicegui.evaluate import ui_evaluator  # type: ignore

    ev = ui_evaluator(origin="NiceGUI:ScanCausality", cache_enabled=True, cache_max=4096)
    return build_causality_trace(
        evaluator=ev,
        base_inputs=base,
        point_overrides=point_overrides,
        constraint_name=domc,
        knobs=knobs,
        rel_step=float(rel_step),
    )


def build_design_families(rep: dict, *, intent: str, min_points: int = 12) -> dict:
    try:
        from tools.design_family_governance_v394 import build_design_families_from_scan_cartography
    except ImportError as exc:
        raise RuntimeError("Design family engine unavailable") from exc
    return build_design_families_from_scan_cartography(rep, intent=str(intent), min_points=int(min_points))


def certify_design_families(art: dict) -> dict:
    try:
        from src.certification.design_family_governance_certification_v394 import (
            certify_design_families_v394,
        )

        return certify_design_families_v394(artifact=art)
    except Exception:
        return {"name": "design_family_governance_v394", "verdict": "UNKNOWN"}


def design_family_table_rows(art: dict) -> List[Dict[str, Any]]:
    fams = art.get("families") if isinstance(art, dict) else None
    if not isinstance(fams, list):
        return []
    rows: List[Dict[str, Any]] = []
    for f in fams:
        if not isinstance(f, dict):
            continue
        x_rng = ""
        y_rng = ""
        if isinstance(f.get("x_min"), (int, float)) and isinstance(f.get("x_max"), (int, float)):
            x_rng = f"[{float(f['x_min']):.3g}, {float(f['x_max']):.3g}]"
        if isinstance(f.get("y_min"), (int, float)) and isinstance(f.get("y_max"), (int, float)):
            y_rng = f"[{float(f['y_min']):.3g}, {float(f['y_max']):.3g}]"
        rows.append(
            {
                "family_id": f.get("family_id"),
                "label": f.get("label"),
                "n_points": f.get("n_points"),
                "feasible_frac": f.get("feasible_frac"),
                "x_range": x_rng,
                "y_range": y_rng,
            }
        )
    return rows


def families_json_bytes(art: dict) -> bytes:
    return json.dumps(art, indent=2, default=str).encode("utf-8")


def apply_probe_to_session(session, rep: dict, cell: dict) -> None:
    cand = probe_promote_inputs(rep, cell)
    for k, v in cand.items():
        if k in session.inputs:
            try:
                session.inputs[k] = float(v)
            except (TypeError, ValueError):
                pass
