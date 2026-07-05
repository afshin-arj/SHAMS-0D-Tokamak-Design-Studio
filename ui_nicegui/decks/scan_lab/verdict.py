"""Scan Lab verdict-first banner."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.scan_helpers import summarize_scan_report


def render_scan_verdict(rep: dict | None) -> None:
    if not isinstance(rep, dict):
        empty_state(
            "No cartography scan results yet. Run a scan below to populate the verdict.",
            kind="info",
        )
        return
    summary = summarize_scan_report(rep)
    if not summary.get("loaded"):
        empty_state("Scan report could not be summarized.", kind="warn")
        return
    ui.label("One-glance truth").classes("text-subtitle1")
    kpi_row([
        ("Dominant constraint", summary["dominant"]),
        (f"Feasible fraction ({summary['intent']})", summary["feasible_pct"]),
        ("Robustness verdict", summary["robustness"]),
        ("Cliffiness proxy", f"{summary['cliffiness']:.2f}"),
    ])
    rs = rep.get("run_seconds")
    if isinstance(rs, (int, float)):
        ui.label(
            f"Scan: {summary['x_key']} vs {summary['y_key']} · "
            f"{summary['n_points']} points · {float(rs):.1f} s"
        ).classes("text-caption text-grey q-mb-sm")
