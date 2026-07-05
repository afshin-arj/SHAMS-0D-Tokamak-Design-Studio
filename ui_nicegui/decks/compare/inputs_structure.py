"""Compare deck — input changes, scenario delta, structural diff."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import (
    embedded_scenario_delta,
    input_diff_rows,
    structural_diff_report,
)


def render_inputs_structure_panel(art_a: dict, art_b: dict) -> None:
    ui.label("Changed PointInputs").classes("text-subtitle2")
    inp_rows = input_diff_rows(art_a, art_b)
    if inp_rows:
        ui.table(
            columns=[
                {"name": "field", "label": "Field", "field": "field", "align": "left"},
                {"name": "A", "label": "A (baseline)", "field": "A"},
                {"name": "B", "label": "B (variant)", "field": "B"},
            ],
            rows=inp_rows,
            row_key="field",
        ).classes("w-full")
    else:
        empty_state("No input differences detected.", kind="info")

    sd = embedded_scenario_delta(art_b)
    ui.label("Embedded scenario_delta (artifact B)").classes("text-subtitle2 q-mt-md")
    if sd:
        ui.json(sd)
    else:
        ui.label(
            "No embedded scenario_delta on B — diffs are computed from inputs/outputs above."
        ).classes("text-caption text-grey")

    ui.label("Structural / schema diff").classes("text-subtitle2 q-mt-md")
    ui.label(
        "Reports constraint set and model-card changes without numeric tolerance."
    ).classes("text-caption text-grey q-mb-xs")
    struct = structural_diff_report(art_a, art_b)
    if not isinstance(struct, dict):
        ui.label("Structural diff unavailable.").classes("text-orange")
        return

    cchg = struct.get("constraints") or {}
    added = cchg.get("added") or []
    removed = cchg.get("removed") or []
    changed = cchg.get("changed_meta") or cchg.get("changed") or []
    with ui.row().classes("gap-4 q-mb-sm"):
        ui.badge(f"+{len(added)} constraints").props("color=positive" if not added else "outline")
        ui.badge(f"−{len(removed)} constraints").props("color=negative" if removed else "outline")
        ui.badge(f"{len(changed)} meta changed").props("outline")

    if added:
        with ui.expansion("Added constraints", icon="add").classes("w-full"):
            ui.markdown("\n".join(f"- `{x}`" for x in added))
    if removed:
        with ui.expansion("Removed constraints", icon="remove").classes("w-full"):
            ui.markdown("\n".join(f"- `{x}`" for x in removed))
    if changed:
        with ui.expansion("Changed constraint metadata", icon="edit").classes("w-full"):
            ui.json(changed)

    mc = struct.get("model_cards") or {}
    if any(mc.get(k) for k in ("added", "removed", "changed")):
        with ui.expansion("Model card diffs", icon="layers").classes("w-full"):
            ui.json(mc)

    with ui.expansion("Raw structural diff (audit JSON)", icon="code").classes("w-full q-mt-sm"):
        ui.code(json.dumps(struct, indent=2, default=str), language="json")
