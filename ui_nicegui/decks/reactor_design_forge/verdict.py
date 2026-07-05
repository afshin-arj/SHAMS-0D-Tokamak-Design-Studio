"""Reactor Design Forge verdict dashboard (Batch 7)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_forge_dashboard(summary: dict | None) -> None:
    ui.label("Forge Status").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary.get("loaded"):
        empty_state(
            "No compiled candidate yet. Use Intent Compiler to propose a candidate, then audit with frozen truth.",
            kind="info",
        )
        return
    kpi_row([
        ("Compiler", summary.get("compiler_status", "-")),
        ("Audit verdict", summary.get("audit_verdict", "-")),
        ("Feasible", "yes" if summary.get("audit_feasible") else ("no" if "audit_feasible" in summary else "-")),
        ("Dominant", summary.get("dominant", "-")),
    ])
