"""Shared archive row handoffs — Promote, Compare, Scan Lab, Systems Mode."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.forge_handoff_helpers import (
    handoff_archive_row_to_scan_lab,
    handoff_archive_row_to_systems_mode,
    send_archive_row_to_compare,
)
from ui_nicegui.lib.forge_machine_finder_helpers import promote_archive_row
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.session import DesignSession


def render_archive_handoffs(
    session: DesignSession,
    run_rep: dict,
    *,
    review_mode: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
    default_row: int = 0,
) -> None:
    archive = run_rep.get("archive") or []
    if not archive:
        ui.label("No archive candidates — run Machine Finder or restore a capsule.").classes(
            "text-caption text-grey"
        )
        return

    ui.label("Cross-deck handoffs").classes("text-subtitle2")
    ui.label(
        "Pick an archive row — promote to Point Designer or send to Compare / Scan Lab / Systems Mode "
        "(targets re-evaluate with frozen truth)."
    ).classes("text-caption text-grey q-mb-sm")

    row_idx = ui.number(
        "Archive row #",
        value=max(0, min(int(default_row), len(archive) - 1)),
        min=0,
        max=max(len(archive) - 1, 0),
        step=1,
    )

    if review_mode:
        ui.label("Review Mode: promotion disabled.").classes("text-orange q-mt-sm")
        return

    def _ix() -> int:
        return int(row_idx.value or 0)

    def _promote() -> None:
        try:
            from ui_nicegui.lib.pd_handoff import invalidate_point_designer_after_seed

            invalidate_point_designer_after_seed(session)
            session.inputs = promote_archive_row(session.inputs, run_rep, _ix())
            session.pd_pending_forge_eval = True
            session.studio_entry_dismissed = True
            navigate_to_point_designer(session)
            ui.notify(
                "Opened Point Designer with archive row inputs — "
                "prior KPIs cleared; Evaluate Point to re-certify.",
                type="warning",
            )
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Promote failed: {exc}", type="negative")

    def _handoff_compare(slot: str) -> None:
        try:
            send_archive_row_to_compare(session, run_rep, _ix(), slot)
            ui.notify(f"Sent archive row to Compare slot {slot}", type="positive")
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    def _to_scan() -> None:
        try:
            handoff_archive_row_to_scan_lab(session, run_rep, _ix())
            switch_deck("Scan Lab", force=True)
            ui.notify("Opened Scan Lab with Forge candidate focus.", type="info")
        except Exception as exc:
            ui.notify(f"Scan Lab handoff failed: {exc}", type="negative")

    def _to_systems() -> None:
        try:
            handoff_archive_row_to_systems_mode(session, run_rep, _ix())
            switch_deck("Systems Mode", force=True)
            ui.notify("Opened Systems Mode with queued candidate.", type="info")
        except Exception as exc:
            ui.notify(f"Systems Mode handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 flex-wrap q-mb-sm"):
        ui.button("Promote → Point Designer", icon="upload", on_click=_promote).props("outline color=primary")
        ui.button("Send → Compare A", icon="compare", on_click=lambda: _handoff_compare("A")).props("flat outline")
        ui.button("Send → Compare B", icon="compare", on_click=lambda: _handoff_compare("B")).props("flat outline")
        ui.button("Focus → Scan Lab", icon="map", on_click=_to_scan).props("flat outline")
        ui.button("Queue → Systems Mode", icon="hub", on_click=_to_systems).props("flat outline")
