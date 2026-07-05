"""Constraint activity timeline from recovery/search traces."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.session import DesignSession


def render_timeline_panel(session: DesignSession) -> None:
    if not session.systems_expert_view:
        return

    with ui.expansion("Constraint activity timeline (expert)", icon="timeline").classes("w-full q-mt-sm"):
        src = ui.radio(
            ["Seeded recovery", "Feasible search"],
            value=session.systems_timeline_src,
            on_change=lambda e: setattr(session, "systems_timeline_src", str(e.value)),
        ).props("inline")
        rows = []
        if str(src.value) == "Seeded recovery":
            rep = session.systems_recovery_last or {}
            for i, t in enumerate(rep.get("trace") or []):
                rows.append({
                    "step": i,
                    "feasible": t.get("feasible"),
                    "V": t.get("V"),
                    "dominant": t.get("dominant", "-"),
                })
        else:
            rep = session.systems_feasible_search_last or {}
            for i, t in enumerate(rep.get("trace") or []):
                hf = list(t.get("hard_failed") or [])
                rows.append({
                    "step": i,
                    "feasible": t.get("feasible"),
                    "V": t.get("V"),
                    "dominant": hf[0] if hf else "-",
                })
        if not rows:
            ui.label("No trace data — enable return_trace in recovery/search.").classes("text-grey")
            return
        ui.table(
            columns=[
                {"name": "step", "label": "#", "field": "step"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
                {"name": "V", "label": "V", "field": "V"},
                {"name": "dominant", "label": "Dominant", "field": "dominant"},
            ],
            rows=rows[:80],
            row_key="step",
        ).classes("w-full")
