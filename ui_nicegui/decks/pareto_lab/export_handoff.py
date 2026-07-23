"""Pareto Lab — Export & Handoff tab."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.compare_helpers import open_compare_deck, send_row_to_compare_slot
from ui_nicegui.lib.pareto_helpers import artifact_to_json_bytes, build_pareto_artifact
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.lib.pareto_interpret_helpers import (
    promote_point_inputs,
    publication_pack_bytes,
    restore_pareto_artifact,
    scan_lab_focus,
    systems_mode_handoff,
    trade_narrative,
)
from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_pareto_artifact_export
from ui_nicegui.session import DesignSession


def render_export_tab(
    session: DesignSession,
    pareto_last: dict | None,
    *,
    on_restore: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Artifacts & handoffs").classes("text-subtitle2")

    async def _upload_replay(e) -> None:
        try:
            payload = json.loads(e.content.read().decode("utf-8"))
            session.pareto_last = restore_pareto_artifact(payload)
            ui.notify("Pareto artifact restored", type="positive")
            if on_restore:
                on_restore()
        except Exception as exc:
            ui.notify(f"Restore failed: {exc}", type="negative")

    ui.upload(on_upload=_upload_replay).props('accept=".json" auto-upload label="Restore Pareto artifact (JSON)"')

    if not isinstance(pareto_last, dict):
        ui.label("Run a study or restore an artifact first.").classes("text-caption text-grey")
        return

    pareto = pareto_last.get("pareto") or []
    bounds = pareto_last.get("bounds") or {}
    narrative = trade_narrative(pareto_last)
    wm_art = watermark_pareto_artifact_export(build_pareto_artifact(pareto_last))
    wm_last = watermark_pareto_artifact_export(pareto_last)

    ui.button(
        "Download Pareto artifact (JSON)",
        icon="download",
        on_click=lambda: ui.download(
            artifact_to_json_bytes(wm_art),
            "shams_pareto_artifact.json",
        ),
    ).props("outline")
    ui.button(
        "Download publication pack (ZIP)",
        icon="folder_zip",
        on_click=lambda: ui.download(
            publication_pack_bytes(wm_last, narrative=narrative),
            "SHAMS_Pareto_PublicationPack.zip",
        ),
    ).props("outline")
    ui.label(
        "PHYS-KPI-001: claim KPIs on infeasible Pareto rows are — (diagnostic) in downloads."
    ).classes("text-caption text-grey q-mt-xs")

    if not pareto:
        return

    ui.separator().classes("q-my-sm")
    ui.label("Promote a frontier point").classes("text-subtitle2")
    idx = ui.number("Row index", value=0, min=0, max=max(len(pareto) - 1, 0), step=1)

    def _promote_pd() -> None:
        i = int(idx.value or 0)
        if i < 0 or i >= len(pareto):
            ui.notify("Invalid row", type="warning")
            return
        promote_point_inputs(session, pareto[i], bounds)
        navigate_to_point_designer(session)
        ui.notify(
            "Opened Point Designer Configure with frontier inputs — "
            "prior KPIs cleared; Evaluate Point to re-certify.",
            type="warning",
        )

    ui.button("Promote to Point Designer", icon="upload", on_click=_promote_pd).props("outline")

    def _handoff_scan() -> None:
        i = int(idx.value or 0)
        if i < 0 or i >= len(pareto):
            ui.notify("Invalid row", type="warning")
            return
        focus = scan_lab_focus(
            pareto[i],
            bounds,
            pareto_last.get("objectives") or {},
            plot_x=session.pareto_plot_x,
            plot_y=session.pareto_plot_y,
        )
        session.scan_probe_focus = focus
        if focus.get("x_key"):
            session.scan_cart_x_key = str(focus["x_key"])
        if focus.get("y_key"):
            session.scan_cart_y_key = str(focus["y_key"])
        session.scan_workflow_step = "2 · Map & Probe"
        switch_deck("Scan Lab", force=True)
        # HANDOFF-TOAST-001: toast only after navigation owns active_deck.
        landed = str(getattr(session, "active_deck", "") or "")
        if landed == "Scan Lab":
            ui.notify("Opened Scan Lab with Pareto focus.", type="info")
        else:
            ui.notify(
                f"Handoff prepared Scan Lab focus, but active deck is {landed or 'unknown'} — check Helm nav.",
                type="warning",
            )

    ui.button("Hand off focus to Scan Lab", icon="map", on_click=_handoff_scan).props("flat outline")

    def _handoff_systems() -> None:
        i = int(idx.value or 0)
        if i < 0 or i >= len(pareto):
            ui.notify("Invalid row", type="warning")
            return
        session.systems_mode_queue = [systems_mode_handoff(pareto[i], bounds)]
        session.systems_workflow_step = "1 · Targets"
        switch_deck("Systems Mode", force=True)
        ui.notify("Opened Systems Mode with queued inputs.", type="info")

    ui.button("Queue for Systems Mode", icon="hub", on_click=_handoff_systems).props("flat outline")

    async def _send_compare(slot: str) -> None:
        i = int(idx.value or 0)
        if i < 0 or i >= len(pareto):
            ui.notify("Invalid row", type="warning")
            return
        try:
            await run.io_bound(
                lambda: send_row_to_compare_slot(
                    session, dict(pareto[i]), slot, label="Pareto Lab frontier"
                )
            )
            ui.notify(f"Sent frontier point to Compare slot {slot}", type="positive")
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Send row → Compare A", icon="compare", on_click=lambda: _send_compare("A")).props("flat outline")
        ui.button("Send row → Compare B", icon="compare", on_click=lambda: _send_compare("B")).props("flat outline")
        ui.button("Open Compare deck", icon="compare_arrows", on_click=lambda: open_compare_deck(session)).props(
            "flat outline"
        )
