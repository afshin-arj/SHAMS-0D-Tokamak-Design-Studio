"""Frontier visualization — precheck / recovery / search traces."""

from __future__ import annotations

import math

from nicegui import ui

from ui_nicegui.session import DesignSession


def render_frontier_panel(session: DesignSession) -> None:
    if not session.systems_expert_view:
        return

    with ui.expansion("Frontier scatter (expert)", icon="scatter_plot").classes("w-full q-mt-sm"):
        src = ui.select(
            ["Precheck samples", "Seeded recovery trace", "Feasible search trace"],
            label="Source",
            value=session.systems_frontier_src,
            on_change=lambda e: setattr(session, "systems_frontier_src", str(e.value)),
        ).classes("w-48")
        x_key = ui.select(
            ["R0_m", "a_m", "Bt_T", "Ti_keV", "Paux_MW", "Ip_MA", "fG", "kappa"],
            label="X variable",
            value=session.systems_frontier_x,
            on_change=lambda e: setattr(session, "systems_frontier_x", str(e.value)),
        ).classes("w-36")
        y_opts = ["Q_DT_eqv", "H98", "q95", "P_e_net_MW", "V (hard violation)"]
        y_key = ui.select(
            y_opts,
            label="Y metric",
            value=session.systems_frontier_y if session.systems_frontier_y in y_opts else y_opts[0],
            on_change=lambda e: setattr(session, "systems_frontier_y", str(e.value)),
        ).classes("w-36")

        pts = _collect_points(session, str(src.value), str(x_key.value), str(y_key.value))
        if not pts:
            ui.label("No points — run precheck, recovery, or search first.").classes("text-grey")
            return

        rows = [{"x": p[0], "y": p[1], "feasible": p[2]} for p in pts[:100]]
        ui.table(
            columns=[
                {"name": "x", "label": "X", "field": "x"},
                {"name": "y", "label": "Y", "field": "y"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
            ],
            rows=rows,
            row_key="x",
        ).classes("w-full")
        n_feas = sum(1 for p in pts if p[2])
        ui.label(f"Points: {len(pts)} | feasible: {n_feas}").classes("text-caption")


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
                yv = float(getattr(sr, "outputs", {}).get(y_key, float("nan")))
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
                    yv = float((t.get("metrics") or {}).get(y_key, float("nan")))
                if math.isfinite(xv) and math.isfinite(yv):
                    pts.append((xv, yv, bool(t.get("feasible"))))
            except Exception:
                continue
    return pts
