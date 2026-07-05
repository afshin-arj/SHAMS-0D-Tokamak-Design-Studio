"""Compare verdict-first summary."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_compare_verdict(summary: dict | None) -> None:
    ui.label("Comparison verdict").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary.get("loaded"):
        empty_state(
            "Load artifacts into Slot A and Slot B to compare mechanism and margin deltas.",
            kind="info",
        )
        return
    kpi_row([
        ("Verdict A", summary.get("verdict_a", "-")),
        ("Verdict B", summary.get("verdict_b", "-")),
        ("Dominant A", summary.get("dominant_a", "-")),
        ("Dominant B", summary.get("dominant_b", "-")),
        ("Largest Δ", summary.get("top_delta", "-")),
    ])
