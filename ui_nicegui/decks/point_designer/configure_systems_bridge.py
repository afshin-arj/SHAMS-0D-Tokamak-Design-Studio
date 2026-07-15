"""Handoff from Point Designer — Scan Lab cartography vs Systems Mode closure."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession


def render_systems_precheck_bridge(session: DesignSession) -> None:
    ui.separator().classes("q-my-md")
    ui.label("Next steps after this point").classes("text-subtitle2")
    ui.label(
        "Point Designer evaluates a single frozen point. Map feasibility with Scan Lab; "
        "use Systems Mode for multistart precheck, Newton solve, and recovery on this baseline."
    ).classes("text-caption q-mb-sm")

    def _go_scan() -> None:
        switch_deck("Scan Lab", force=True)
        ui.notify("Opened Scan Lab — pick two axes and run cartography.", type="info")

    def _go_precheck() -> None:
        session.pd_pending_systems_action = "precheck"
        session.systems_workflow_step = "2 · Check & Solve"
        switch_deck("Systems Mode", force=True)
        ui.notify("Point Designer handoff — run Step ① precheck on Check & Solve.", type="info")

    with ui.row().classes("w-full gap-2 flex-wrap"):
        ui.button(
            "Map design space (Scan Lab)",
            icon="map",
            on_click=_go_scan,
        ).props("outline color=primary").classes("flex-1")
        ui.button(
            "Systems closure / recovery (Systems Mode)",
            icon="hub",
            on_click=_go_precheck,
        ).props("outline").classes("flex-1")
