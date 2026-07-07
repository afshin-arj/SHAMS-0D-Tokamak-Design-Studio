"""Control Room — scenario delta between two run artifacts."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.compare_helpers import (
    bridge_compare_slots_to_cr,
    bridge_cr_to_compare_slots,
    input_diff_rows,
    numeric_output_diff_rows,
    structural_diff_report,
)
from ui_nicegui.lib.cr_artifacts_helpers import load_json_bytes
from ui_nicegui.lib.navigation import switch_deck
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

    with ui.expansion("Compare deck bridge", icon="compare", value=False).classes("w-full q-mt-sm"):
        ui.label(
            "Bidirectional handoff with the **Compare** deck — baseline → slot A, scenario → slot B."
        ).classes("text-caption text-grey q-mb-sm")

        def _to_compare() -> None:
            ok_a, ok_b = bridge_cr_to_compare_slots(session)
            if ok_a or ok_b:
                parts = []
                if ok_a:
                    parts.append("A")
                if ok_b:
                    parts.append("B")
                ui.notify(f"Loaded Control Room artifacts into Compare slot(s) {'/'.join(parts)}", type="positive")
            else:
                ui.notify("Upload baseline and/or scenario artifacts first.", type="warning")

        def _from_compare() -> None:
            ok_a, ok_b = bridge_compare_slots_to_cr(session)
            if ok_a or ok_b:
                _delta.refresh(session)
                ui.notify("Loaded Compare slots into Scenario Delta.", type="positive")
            else:
                ui.notify("Compare slots A/B are empty.", type="warning")

        def _open_compare() -> None:
            bridge_cr_to_compare_slots(session)
            session.cmp_workflow_step = "1 · Load A & B"
            switch_deck("Compare")
            ui.notify("Opened Compare with scenario pair.", type="info")

        with ui.row().classes("gap-2 flex-wrap"):
            ui.button("Send to Compare slots", icon="compare", on_click=_to_compare).props("outline")
            ui.button("Load from Compare slots", icon="download", on_click=_from_compare).props("flat outline")
            ui.button("Open full Compare deck", icon="open_in_new", on_click=_open_compare).props("flat")

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
