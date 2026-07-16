"""Trade Study — Export & Handoff tab."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.compare_helpers import open_compare_deck, send_row_to_compare_slot
from ui_nicegui.lib.pareto_interpret_helpers import scan_lab_focus, systems_mode_handoff
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.lib.trade_interpret_helpers import (
    capsule_from_restore,
    promote_row,
    restore_study_capsule,
    study_narrative,
)
from ui_nicegui.lib.trade_study_helpers import report_to_json_bytes
from ui_nicegui.session import DesignSession


def render_export_tab(
    session: DesignSession,
    rep: dict | None,
    *,
    on_restore: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Study artifacts").classes("text-subtitle2")

    async def _upload(e) -> None:
        try:
            payload = json.loads(e.content.read().decode("utf-8"))
            if payload.get("schema") == "shams.study_capsule.v1":
                session.active_study_capsule = dict(payload)
                session.trade_last = restore_study_capsule(payload)
            else:
                session.trade_last = restore_study_capsule(payload)
                session.active_study_capsule = capsule_from_restore(session.trade_last)
            ui.notify("Study restored", type="positive")
            if on_restore:
                on_restore()
        except Exception as exc:
            ui.notify(f"Restore failed: {exc}", type="negative")

    ui.upload(on_upload=_upload).props('accept=".json" auto-upload label="Restore study report or capsule (JSON)"')

    if not isinstance(rep, dict):
        ui.label("Run a study or restore an artifact first.").classes("text-caption text-grey")
        return

    ui.button(
        "Download study report (JSON)",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(rep), "shams_trade_study.json"),
    ).props("outline")
    if session.active_study_capsule:
        ui.button(
            "Download study capsule (JSON)",
            icon="download",
            on_click=lambda: ui.download(
                report_to_json_bytes(session.active_study_capsule),
                "shams_study_capsule.json",
            ),
        ).props("outline flat")
    ui.button(
        "Download narrative (Markdown)",
        icon="description",
        on_click=lambda: ui.download(study_narrative(rep).encode("utf-8"), "trade_study_summary.md"),
    ).props("flat outline")

    pareto = rep.get("pareto") or []
    if not pareto:
        return

    bounds = (rep.get("meta") or {}).get("bounds") or {}
    bound_keys = [k for k in bounds if isinstance(bounds.get(k), (list, tuple))]

    ui.separator().classes("q-my-sm")
    ui.label("Promote a Pareto point").classes("text-subtitle2")
    idx = ui.number("Row index (i)", value=0, min=0, max=max(len(pareto) - 1, 0), step=1)

    def _promote() -> None:
        i = int(idx.value or 0)
        row = next((r for r in pareto if int(r.get("i", -1)) == i), None)
        if row is None and 0 <= i < len(pareto):
            row = pareto[i]
        if row is None:
            ui.notify("Invalid row", type="warning")
            return
        promote_row(session, row, bound_keys)
        navigate_to_point_designer(session)
        ui.notify("Opened Point Designer Configure with study inputs.", type="positive")

    ui.button("Promote to Point Designer", icon="upload", on_click=_promote).props("outline")

    def _send_compare(slot: str) -> None:
        i = int(idx.value or 0)
        row = next((r for r in pareto if int(r.get("i", -1)) == i), None)
        if row is None and 0 <= i < len(pareto):
            row = pareto[i]
        if row is None:
            ui.notify("Invalid row", type="warning")
            return
        try:
            send_row_to_compare_slot(session, dict(row), slot, label="Trade Study Pareto")
            ui.notify(f"Sent Pareto row to Compare slot {slot}", type="positive")
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Send row → Compare A", icon="compare", on_click=lambda: _send_compare("A")).props("flat outline")
        ui.button("Send row → Compare B", icon="compare", on_click=lambda: _send_compare("B")).props("flat outline")
        ui.button("Open Compare deck", icon="compare_arrows", on_click=lambda: open_compare_deck(session)).props(
            "flat outline"
        )

    objectives = (rep.get("meta") or {}).get("objectives") or {}

    def _handoff_scan() -> None:
        i = int(idx.value or 0)
        row = next((r for r in pareto if int(r.get("i", -1)) == i), None)
        if row is None and 0 <= i < len(pareto):
            row = pareto[i]
        if row is None:
            ui.notify("Invalid row", type="warning")
            return
        focus = scan_lab_focus(row, bounds, objectives)
        focus["source"] = "Trade Study Studio"
        session.scan_probe_focus = focus
        if focus.get("x_key"):
            session.scan_cart_x_key = str(focus["x_key"])
        if focus.get("y_key"):
            session.scan_cart_y_key = str(focus["y_key"])
        session.scan_workflow_step = "1 · Setup & Run"
        switch_deck("Scan Lab", force=True)
        ui.notify("Opened Scan Lab with trade-study focus.", type="info")

    def _handoff_systems() -> None:
        i = int(idx.value or 0)
        row = next((r for r in pareto if int(r.get("i", -1)) == i), None)
        if row is None and 0 <= i < len(pareto):
            row = pareto[i]
        if row is None:
            ui.notify("Invalid row", type="warning")
            return
        session.systems_mode_queue = [systems_mode_handoff(row, bounds)]
        session.systems_workflow_step = "1 · Targets"
        switch_deck("Systems Mode", force=True)
        ui.notify("Opened Systems Mode with queued inputs.", type="info")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Hand off focus to Scan Lab", icon="map", on_click=_handoff_scan).props("flat outline")
        ui.button("Queue for Systems Mode", icon="hub", on_click=_handoff_systems).props("flat outline")
