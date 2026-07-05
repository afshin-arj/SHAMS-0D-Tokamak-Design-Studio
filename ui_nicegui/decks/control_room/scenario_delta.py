"""Control Room — scenario delta between two run artifacts."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.compare_helpers import input_diff_rows, numeric_output_diff_rows, structural_diff_report
from ui_nicegui.lib.cr_artifacts_helpers import load_json_bytes
from ui_nicegui.session import DesignSession


def render_scenario_delta(session: DesignSession) -> None:
    ui.label("Scenario Delta").classes("text-subtitle1")
    ui.label(
        "Compare baseline vs scenario artifacts. Uses embedded scenario_delta when present; "
        "otherwise computes transparent input/output/structural diffs."
    ).classes("text-caption text-grey q-mb-sm")

    with ui.row().classes("w-full gap-md"):
        async def _base(e) -> None:
            try:
                session.cr_scenario_base = load_json_bytes(e.content.read())
                ui.notify("Baseline loaded", type="positive")
                _delta.refresh(session)
            except Exception as exc:
                ui.notify(f"Baseline load failed: {exc}", type="negative")

        async def _variant(e) -> None:
            try:
                session.cr_scenario_variant = load_json_bytes(e.content.read())
                ui.notify("Scenario loaded", type="positive")
                _delta.refresh(session)
            except Exception as exc:
                ui.notify(f"Scenario load failed: {exc}", type="negative")

        with ui.column().classes("flex-1"):
            ui.upload(on_upload=_base).props('accept=".json" auto-upload label="Baseline artifact"')
        with ui.column().classes("flex-1"):
            ui.upload(on_upload=_variant).props('accept=".json" auto-upload label="Scenario artifact"')

    _delta(session)


@ui.refreshable
def _delta(session: DesignSession) -> None:
    base = session.cr_scenario_base
    scen = session.cr_scenario_variant
    if not isinstance(base, dict) or not isinstance(scen, dict):
        ui.label("Upload both baseline and scenario artifacts.").classes("text-grey")
        return

    sd = scen.get("scenario_delta")
    with ui.expansion("Embedded scenario_delta", icon="difference").classes("w-full"):
        if sd:
            ui.json(sd)
        else:
            ui.label("No embedded scenario_delta — computed diffs below.").classes("text-caption")

    in_rows = input_diff_rows(base, scen)
    ui.label("Changed inputs").classes("text-subtitle2 q-mt-sm")
    if in_rows:
        ui.table(
            columns=[
                {"name": "field", "label": "field", "field": "field", "align": "left"},
                {"name": "A", "label": "baseline", "field": "A", "align": "left"},
                {"name": "B", "label": "scenario", "field": "B", "align": "left"},
            ],
            rows=in_rows,
            row_key="field",
        ).classes("w-full")
    else:
        ui.label("No input differences.").classes("text-caption")

    out_rows = numeric_output_diff_rows(base, scen)
    ui.label("Numeric output deltas").classes("text-subtitle2 q-mt-sm")
    if out_rows:
        ui.table(
            columns=[
                {"name": "metric", "label": "metric", "field": "metric", "align": "left"},
                {"name": "A", "label": "baseline", "field": "A", "align": "left"},
                {"name": "B", "label": "scenario", "field": "B", "align": "left"},
                {"name": "B-A", "label": "B-A", "field": "B-A", "align": "left"},
            ],
            rows=out_rows,
            row_key="metric",
        ).classes("w-full")
    else:
        ui.label("No numeric output differences.").classes("text-caption")

    ui.label("Structural / schema diff").classes("text-subtitle2 q-mt-sm")
    struct = structural_diff_report(base, scen)
    if isinstance(struct, dict):
        cchg = struct.get("constraints") or {}
        ui.label(
            f"Constraints: +{len(cchg.get('added') or [])} "
            f"/ −{len(cchg.get('removed') or [])} "
            f"/ meta Δ{len(cchg.get('changed_meta') or [])}"
        ).classes("text-caption")
        with ui.expansion("Full structural diff", icon="account_tree").classes("w-full"):
            ui.json(struct)
    else:
        ui.label("Structural diff unavailable.").classes("text-grey")
