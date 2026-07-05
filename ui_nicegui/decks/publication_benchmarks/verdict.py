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
    ])
    conf = summary.get("design_confidence", "UNKNOWN")
    posture = summary.get("decision_posture", "UNKNOWN")
    ui.label(
        f"{summary.get('preset_label')} · intent={summary.get('selected_intent')} "
        f"(native: {summary.get('native_intent')}) · stamp {summary.get('stamp', '-')}…"
    ).classes("text-caption text-grey")
    ui.label(f"Design confidence: {conf} · Decision posture: {posture}").classes("text-caption")
    fl = summary.get("fidelity_label") or ""
    if fl:
        ui.label(f"Fidelity tier: {fl}").classes("text-caption")
    risk = summary.get("primary_risk_driver") or ""
    if risk:
        ui.label(f"Primary risk driver: {risk}").classes("text-caption text-orange")
    epoch = summary.get("epoch_overall") or ""
    if epoch:
        ui.label(f"Epoch feasibility (overall): {epoch}").classes("text-caption q-mt-xs")
    rows = summary.get("epoch_rows") or []
    if rows:
        ui.table(
            columns=[
                {"name": "epoch", "label": "Epoch", "field": "epoch", "align": "left"},
                {"name": "verdict", "label": "Verdict", "field": "verdict"},
            ],
            rows=rows,
            row_key="epoch",
        ).classes("w-full q-mt-xs")
