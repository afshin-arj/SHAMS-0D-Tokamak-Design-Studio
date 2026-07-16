"""Compare verdict-first summary."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.session import DesignSession


def render_compare_verdict(summary: dict | None, *, session: DesignSession | None = None) -> None:
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
    kpi_row([
        ("Q A", summary.get("q_a", "-")),
        ("Q B", summary.get("q_b", "-")),
        ("H98 A", summary.get("h98_a", "-")),
        ("H98 B", summary.get("h98_b", "-")),
        ("Pfus A [MW]", summary.get("pfus_a", "-")),
        ("Pfus B [MW]", summary.get("pfus_b", "-")),
    ])

    sub_rows = summary.get("subsystem_diff") or []
    changed = [r for r in sub_rows if isinstance(r, dict) and r.get("changed")]
    expert = bool(getattr(session, "cmp_expert_view", False)) if session else False
    show_sub = expert or bool(changed)
    if show_sub and sub_rows:
        with ui.expansion(
            "Subsystem pass/fail (governance groups)",
            icon="grid_view",
            value=expert or bool(changed),
        ).classes("w-full q-mt-sm"):
            ui.label(
                "Pass/fail by engineering subsystem — highlights where B regressed vs A."
            ).classes("text-caption text-grey q-mb-xs")
            ui.table(
                columns=[
                    {"name": "subsystem", "label": "Subsystem", "field": "subsystem", "align": "left"},
                    {"name": "A", "label": "A", "field": "A"},
                    {"name": "B", "label": "B", "field": "B"},
                    {"name": "changed", "label": "Changed?", "field": "changed"},
                ],
                rows=sub_rows,
                row_key="subsystem",
            ).classes("w-full")
