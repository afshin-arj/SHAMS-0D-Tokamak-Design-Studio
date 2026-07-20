"""Compare deck — performance KPIs and output deltas."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import kpi_diff_rows, metric_diff_rows, numeric_output_diff_rows
from ui_nicegui.lib.compare_labels import METRIC_DISPLAY
from ui_nicegui.session import DesignSession


def render_metrics_panel(session: DesignSession, art_a: dict, art_b: dict) -> None:
    from ui_nicegui.lib.verdict_core import verdict_summary

    ui.label("Key performance metrics").classes("text-subtitle2")
    out_a = (art_a.get("outputs") if isinstance(art_a, dict) else None) or {}
    out_b = (art_b.get("outputs") if isinstance(art_b, dict) else None) or {}
    feas_a = bool(verdict_summary(out_a).get("feasible")) if out_a else False
    feas_b = bool(verdict_summary(out_b).get("feasible")) if out_b else False
    achievement = {
        "Q",
        "Q_DT_eqv",
        "H98",
        "Pfus_total_MW",
        "P_fus_MW",
        "P_e_net_MW",
        "P_net_e_MW",
        "Pnet_MWe",
    }
    if not feas_a or not feas_b:
        ui.label(
            "PHYS-KPI-001: Q / H98 / Pfus / P_net on INFEASIBLE slots are diagnostic residue — not design claims."
        ).classes("text-caption text-orange q-mb-xs")

    rows = metric_diff_rows(art_a, art_b)
    if rows:
        display_rows = []
        for r in rows:
            key = str(r.get("metric", ""))
            row = {
                **r,
                "label": METRIC_DISPLAY.get(key, key),
            }
            if key in achievement:
                if not feas_a:
                    row["A"] = "— (diagnostic)"
                if not feas_b:
                    row["B"] = "— (diagnostic)"
                if not feas_a or not feas_b:
                    row["B-A"] = "—"
            display_rows.append(row)
        ui.table(
            columns=[
                {"name": "label", "label": "Metric", "field": "label", "align": "left"},
                {"name": "A", "label": "A (baseline)", "field": "A"},
                {"name": "B", "label": "B (variant)", "field": "B"},
                {"name": "B-A", "label": "Δ B−A", "field": "B-A"},
            ],
            rows=display_rows,
            row_key="metric",
        ).classes("w-full")
    else:
        empty_state("No comparable key metrics in both artifacts.", kind="warn")

    kpi_rows = kpi_diff_rows(art_a, art_b)
    if kpi_rows:
        ui.label("Artifact KPI block").classes("text-subtitle2 q-mt-md")
        if not feas_a or not feas_b:
            ui.label("KPI block values inherit slot feasibility — treat INFEASIBLE as diagnostic.").classes(
                "text-caption text-orange"
            )
        ui.table(
            columns=[
                {"name": "kpi", "label": "KPI", "field": "kpi", "align": "left"},
                {"name": "A", "label": "A", "field": "A"},
                {"name": "B", "label": "B", "field": "B"},
                {"name": "B-A", "label": "Δ", "field": "B-A"},
            ],
            rows=kpi_rows,
            row_key="kpi",
        ).classes("w-full")

    ui.separator().classes("q-my-sm")

    @ui.refreshable
    def _all_outputs_section() -> None:
        if not session.cmp_show_all_outputs:
            return
        all_rows = numeric_output_diff_rows(art_a, art_b)
        if all_rows:
            ui.table(
                columns=[
                    {"name": "metric", "label": "Output", "field": "metric", "align": "left"},
                    {"name": "A", "label": "A", "field": "A"},
                    {"name": "B", "label": "B", "field": "B"},
                    {"name": "B-A", "label": "Δ", "field": "B-A"},
                    {"name": "frac", "label": "Δ/A", "field": "frac"},
                ],
                rows=all_rows,
                row_key="metric",
            ).classes("w-full")
        else:
            ui.label("No numeric output differences detected.").classes("text-caption text-grey")

    ui.switch(
        "Show all numeric output deltas (sorted by |Δ|)",
        value=session.cmp_show_all_outputs,
        on_change=lambda e: (
            setattr(session, "cmp_show_all_outputs", bool(e.value)),
            _all_outputs_section.refresh(),
        ),
    )
    _all_outputs_section()
