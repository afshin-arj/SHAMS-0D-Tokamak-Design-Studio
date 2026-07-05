"""Trade Study — Interpret & Families tab."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.trade_interpret_helpers import blocking_constraints, study_narrative
from ui_nicegui.session import DesignSession


def render_interpret_tab(session: DesignSession, rep: dict) -> None:
    records = rep.get("records") or []
    summary = rep.get("summary") or {}
    fam = rep.get("family_summary") or {}

    ui.label("Study audit").classes("text-subtitle2")
    ui.markdown(study_narrative(rep)).classes("text-caption")

    with ui.expansion("Self-audit checklist", icon="fact_check", value=session.trade_teaching_mode).classes("w-full"):
        checks = [
            ("Knob set recorded", bool(summary.get("knob_set") or rep.get("knob_set_name"))),
            ("Objectives declared", bool((rep.get("meta") or {}).get("objectives"))),
            ("Feasible samples exist", int(summary.get("n_feasible", 0)) > 0),
            ("Pareto subset produced", int(summary.get("n_pareto", 0)) > 0),
            ("Seed recorded", summary.get("seed") is not None),
            ("Study capsule active", isinstance(session.active_study_capsule, dict)),
        ]
        for label, ok in checks:
            ui.label(f"{'✓' if ok else '✗'} {label}").classes(
                "text-caption" + (" text-positive" if ok else " text-orange")
            )

    blockers = blocking_constraints(records)
    if blockers:
        ui.label("Top blocking constraints (infeasible samples)").classes("text-subtitle2 q-mt-md")
        for name, n in blockers:
            ui.label(f"{name}: {n}").classes("text-caption")

    fam_rows = fam.get("rows") if isinstance(fam, dict) else None
    if isinstance(fam_rows, list) and fam_rows:
        ui.label("Design family mix").classes("text-subtitle2 q-mt-md")
        ui.table(
            columns=[
                {"name": "family", "label": "Family", "field": "family", "align": "left"},
                {"name": "title", "label": "Title", "field": "title", "align": "left"},
                {"name": "n", "label": "N", "field": "n"},
                {"name": "n_feasible", "label": "Feasible", "field": "n_feasible"},
                {"name": "feasible_frac", "label": "Feasible frac", "field": "feasible_frac"},
            ],
            rows=[r for r in fam_rows if isinstance(r, dict)][:30],
            row_key="family",
        ).classes("w-full")

    ui.separator().classes("q-my-sm")
    ui.label(f"Lane mode at run: {session.trade_last_lane or 'Nominal only'}").classes("text-caption text-grey")
