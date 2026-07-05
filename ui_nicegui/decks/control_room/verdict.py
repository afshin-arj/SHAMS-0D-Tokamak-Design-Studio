"""Control Room governance verdict row (Batch 10)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row


def render_governance_verdict(summary: dict) -> None:
    ui.label("Governance posture").classes("text-subtitle1")
    hygiene = "OK" if summary.get("hygiene_ok") else "Issues"
    kpi_row([
        ("Version", summary.get("version", "-")),
        ("Active deck", summary.get("active_deck", "-")),
        ("Point verdict", summary.get("point_verdict", "-")),
        ("Hygiene", hygiene),
    ])
