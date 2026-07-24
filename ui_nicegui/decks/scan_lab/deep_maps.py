"""Scan Lab advanced landscape maps — iso-manifolds, vector field, coupling, intent-split."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.scan_deep_viz_helpers import (
    constraint_names_from_report,
    coupling_matrix_rows,
    intent_split_overlay_figure,
    plotly_iso_contour_figure,
    plotly_margin_vector_figure,
    robustness_label_counts,
)
from ui_nicegui.lib.scan_workbench_helpers import dominance_map_png_bytes
from ui_nicegui.session import DesignSession


def render_deep_landscape_maps(
    session: DesignSession,
    rep: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    intents = list(rep.get("intents") or session.scan_cart_intents or ["Reactor"])
    if session.scan_deep_viz_intent not in intents:
        session.scan_deep_viz_intent = str(intents[0])

    ui.label("Advanced landscape maps").classes("text-subtitle1")
    ui.label(
        "Descriptive-only views over the scan grid — iso-boundaries, margin gradients, and constraint coupling."
    ).classes("text-caption q-mb-sm")

    ui.select(
        intents,
        label="Intent lens",
        value=session.scan_deep_viz_intent,
        on_change=lambda e: (
            setattr(session, "scan_deep_viz_intent", str(e.value)),
            _maps.refresh(),
        ),
    ).classes("w-full q-mb-sm")

    if len(intents) >= 2 and "Research" in intents and "Reactor" in intents:
        ui.label(
            "Intent-split: orange overlay marks Research-feasible but Reactor-infeasible cells."
        ).classes("text-caption text-orange q-mb-xs")

    _maps(session, rep, intents)


@ui.refreshable
def _maps(session: DesignSession, rep: dict, intents: list) -> None:
    it = session.scan_deep_viz_intent
    names = constraint_names_from_report(rep)
    if names:
        if session.scan_iso_constraint not in names:
            session.scan_iso_constraint = names[0]
        ui.select(
            names,
            label="Iso-contour constraint (margin = 0)",
            value=session.scan_iso_constraint,
            on_change=lambda e: setattr(session, "scan_iso_constraint", str(e.value)),
        ).classes("w-full q-mb-sm")
        try:
            fig = plotly_iso_contour_figure(rep, it, session.scan_iso_constraint)
            ui.plotly(fig).classes("w-full")
        except Exception as exc:
            ui.label(f"Iso-contour unavailable: {exc}").classes("text-caption text-negative")

    xn = len(rep.get("x_vals") or [])
    yn = len(rep.get("y_vals") or [])
    with ui.expansion("Margin gradient field", icon="swap_calls").classes("w-full"):
        if xn < 3 or yn < 3:
            ui.label("Requires scan resolution Nx,Ny ≥ 3.").classes("text-caption text-orange")
        else:
            try:
                ui.plotly(plotly_margin_vector_figure(rep, it)).classes("w-full")
            except Exception as exc:
                ui.label(str(exc)).classes("text-caption text-negative")

    counts = robustness_label_counts(rep, it)
    if counts:
        with ui.expansion("Cell neighborhood labels (counts)", icon="analytics").classes("w-full"):
            ui.label(
                "Robust / Balanced / Brittle / Knife-edge = local p-feasible neighborhood — "
                "not L0 FEASIBLE/INFEASIBLE (an infeasible cell can still count as Robust)."
            ).classes("text-caption text-orange q-mb-xs")
            total = sum(counts.values()) or 1
            for lab, n in sorted(counts.items(), key=lambda x: -x[1]):
                ui.label(f"{lab}: {n} ({100.0 * n / total:.0f}%)").classes("text-caption")

    col_names, rows = coupling_matrix_rows(rep, it)
    with ui.expansion("Constraint coupling matrix", icon="hub").classes("w-full"):
        ui.label("How often constraint A appears before B in local failure order.").classes("text-caption")
        if rows and col_names:
            ui.table(
                columns=[{"name": "from", "label": "From \\ To", "field": "from", "align": "left"}]
                + [{"name": c, "label": c, "field": c} for c in col_names],
                rows=rows,
                row_key="from",
            ).classes("w-full")
        else:
            ui.label("Interaction data unavailable in this report.").classes("text-caption text-grey")

    if len(intents) >= 2 and "Research" in intents and "Reactor" in intents:
        with ui.expansion("Intent-split overlay", icon="compare").classes("w-full"):
            try:
                ui.plotly(intent_split_overlay_figure(rep)).classes("w-full")
            except Exception as exc:
                ui.label(str(exc)).classes("text-caption text-negative")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        for intent in intents:
            ui.button(
                f"Download map PNG — {intent}",
                icon="download",
                on_click=lambda r=rep, i=intent: ui.download(
                    dominance_map_png_bytes(r, i), f"shams_scan_map_{i.lower()}.png"
                ),
            ).props("flat outline")
