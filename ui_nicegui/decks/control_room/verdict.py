"""Control Room governance verdict row."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row


def render_governance_verdict(summary: dict) -> None:
    ui.label("Governance posture").classes("text-subtitle1")
    fh = summary.get("feasible_hard")
    fh_label = "-" if fh is None else ("YES" if fh else "NO")
    kpi_row([
        ("Verdict", summary.get("point_verdict", "-")),
        ("Dominant", summary.get("dominant", "-")),
        ("Q / nτE", summary.get("q_label", "-")),
        ("Design class", summary.get("design_class", "-")),
        ("Hard feasible", fh_label),
        ("Version", summary.get("version", "-")),
    ])
