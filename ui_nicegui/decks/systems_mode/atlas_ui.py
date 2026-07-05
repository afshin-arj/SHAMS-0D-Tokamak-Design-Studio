"""Micro feasibility atlas — 2D slice with heatmap and cartography."""

from __future__ import annotations

import base64

from nicegui import run, ui

from ui_nicegui.lib.systems_atlas_plot import atlas_heatmap_png
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.session import DesignSession


def render_atlas_panel(session: DesignSession) -> None:
    with ui.expansion("Feasibility map (2D slice)", icon="grid_on").classes("w-full q-mt-sm"):
        ui.label(
            "Sweep two iteration variables over a small grid. "
            "Each cell shows the dominant hard constraint — deterministic screening, not a full solve."
        ).classes("text-caption q-mb-sm")

        base, _, variables = resolve_systems_problem(session)
        var_names = list(variables.keys()) or ["Paux_MW", "Ip_MA"]
        if session.systems_atlas_var_x not in var_names:
            session.systems_atlas_var_x = var_names[0]
        if session.systems_atlas_var_y not in var_names and len(var_names) > 1:
            session.systems_atlas_var_y = var_names[1]

        with ui.row().classes("gap-4 flex-wrap"):
            ui.select(
                var_names,
                label="Horizontal axis",
                value=session.systems_atlas_var_x,
                on_change=lambda e: setattr(session, "systems_atlas_var_x", str(e.value)),
            ).classes("w-40")
            ui.select(
                var_names,
                label="Vertical axis",
                value=session.systems_atlas_var_y,
                on_change=lambda e: setattr(session, "systems_atlas_var_y", str(e.value)),
            ).classes("w-40")
            ui.number(
                "Grid size",
                value=session.systems_atlas_grid_n,
                min=5,
                max=31,
                step=1,
                on_change=lambda e: setattr(session, "systems_atlas_grid_n", int(e.value or 12)),
            ).classes("w-24")
            ui.number(
                "Robust margin threshold",
                value=getattr(session, "systems_atlas_robust_thr", 0.10),
                min=0.0,
                max=0.5,
                step=0.01,
                on_change=lambda e: setattr(session, "systems_atlas_robust_thr", float(e.value or 0.10)),
            ).classes("w-36")

        async def _compute() -> None:
            if session.systems_atlas_var_x == session.systems_atlas_var_y:
                ui.notify("Pick two different variables", type="warning")
                return
            ui.notify("Computing feasibility map…", type="info")
            b, _, v = resolve_systems_problem(session)

            def _run():
                try:
                    from src.systems.atlas import compute_micro_atlas
                except ImportError:
                    from systems.atlas import compute_micro_atlas  # type: ignore
                return compute_micro_atlas(
                    b,
                    v,
                    session.systems_atlas_var_x,
                    session.systems_atlas_var_y,
                    nx=int(session.systems_atlas_grid_n),
                    ny=int(session.systems_atlas_grid_n),
                )

            atlas = await run.io_bound(_run)
            session.systems_last_micro_atlas = atlas
            _atlas_view.refresh()

        ui.button("Compute map", icon="map", on_click=_compute).props("outline q-mb-sm")
        _atlas_view(session)


@ui.refreshable
def _atlas_view(session: DesignSession) -> None:
    atlas = session.systems_last_micro_atlas
    if not isinstance(atlas, dict):
        return
    if not atlas.get("ok", True) and atlas.get("reason"):
        ui.label(f"Map unavailable: {atlas.get('reason')}").classes("text-orange")
        return

    png = atlas_heatmap_png(
        atlas,
        title=f"Dominant limiter — {atlas.get('var_x', 'X')} vs {atlas.get('var_y', 'Y')}",
    )
    if png:
        ui.image(f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}").classes("w-full max-w-2xl")
    else:
        ui.label("Heatmap unavailable — see cell table below.").classes("text-caption text-grey")

    dom = atlas.get("dominant") or []
    n_pass = sum(1 for row in dom for c in row if str(c).lower() in ("ok", "pass", ""))
    n_total = sum(len(row) for row in dom) if dom else 0
    ui.label(f"Cells: {n_total} | feasible-dominant: {n_pass}").classes("text-caption q-mt-sm")

    try:
        from src.systems.cartography2 import classify_cells, label_fractions, mechanism_histogram, mechanism_group_histogram
    except ImportError:
        from systems.cartography2 import (  # type: ignore
            classify_cells,
            label_fractions,
            mechanism_histogram,
            mechanism_group_histogram,
        )

    thr = float(getattr(session, "systems_atlas_robust_thr", 0.10))
    c2 = classify_cells(atlas, robust_margin_min=thr)
    if isinstance(c2, dict) and c2.get("ok"):
        fr = label_fractions(c2.get("labels") or [])
        with ui.row().classes("gap-4 q-mb-sm"):
            ui.label(f"Robust: {100.0 * fr.get('robust', 0.0):.1f}%").classes("text-caption")
            ui.label(f"Fragile: {100.0 * fr.get('fragile', 0.0):.1f}%").classes("text-caption")
            ui.label(f"Empty: {100.0 * fr.get('empty', 0.0):.1f}%").classes("text-caption")

        gh = mechanism_group_histogram(atlas)
        if gh:
            rows_g = []
            total_fail = max(1, sum(gh.values()))
            for k, v in sorted(gh.items(), key=lambda kv: kv[1], reverse=True)[:10]:
                rows_g.append({"group": k, "cells": int(v), "share": f"{100.0 * float(v) / total_fail:.1f}%"})
            ui.table(
                columns=[
                    {"name": "group", "label": "Mechanism group", "field": "group", "align": "left"},
                    {"name": "cells", "label": "Cells", "field": "cells"},
                    {"name": "share", "label": "Share", "field": "share"},
                ],
                rows=rows_g,
                row_key="group",
            ).classes("w-full q-mb-sm")

    hist = mechanism_histogram(atlas) if dom else {}
    if hist:
        rows = []
        total = max(1, sum(hist.values()))
        for k, v in sorted(hist.items(), key=lambda kv: kv[1], reverse=True):
            if k == "ok":
                continue
            rows.append({"mechanism": k, "cells": int(v), "share": f"{100.0 * float(v) / total:.1f}%"})
            if len(rows) >= 12:
                break
        if rows:
            with ui.expansion("Failing mechanisms in slice", icon="analytics").classes("w-full"):
                ui.table(
                    columns=[
                        {"name": "mechanism", "label": "Mechanism", "field": "mechanism", "align": "left"},
                        {"name": "cells", "label": "Cells", "field": "cells"},
                        {"name": "share", "label": "Share", "field": "share"},
                    ],
                    rows=rows,
                    row_key="mechanism",
                ).classes("w-full")

    with ui.expansion("Raw grid coordinates", icon="data_object").classes("w-full"):
        ui.json({
            "var_x": atlas.get("var_x"),
            "var_y": atlas.get("var_y"),
            "xs": atlas.get("xs"),
            "ys": atlas.get("ys"),
        })
