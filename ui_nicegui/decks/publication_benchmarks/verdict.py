"""Constitutional Atlas verdict banner."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row


def render_atlas_verdict(summary: dict | None) -> None:
    ui.label("Atlas verdict").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary.get("loaded"):
        empty_state(
            "Select a tokamak preset and evaluate under Research or Reactor intent.",
            kind="info",
        )
        return
    wm = summary.get("worst_hard_margin")
    wm_s = f"{float(wm):.3f}" if isinstance(wm, (int, float)) and wm == wm else "-"
    kpi_row([
        ("Verdict", summary.get("verdict", "-")),
        ("Dominant mechanism", summary.get("dominant_mechanism", "-")),
        ("Dominant constraint", summary.get("dominant_constraint", "-")),
        ("Worst hard margin", wm_s),
        ("Stamp", summary.get("stamp", "-")),
    ])
    ui.label(
        f"{summary.get('preset_label')} · intent={summary.get('selected_intent')} "
        f"(native: {summary.get('native_intent')})"
    ).classes("text-caption text-grey q-mb-sm")
