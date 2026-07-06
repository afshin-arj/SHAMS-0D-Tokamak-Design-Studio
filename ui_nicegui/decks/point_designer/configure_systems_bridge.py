"""Handoff from Point Designer to Systems Mode precheck."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession


def render_systems_precheck_bridge(session: DesignSession) -> None:
    ui.separator().classes("q-my-md")
    ui.label("Outer-loop exploration").classes("text-subtitle2")
    ui.label(
        "Point Designer evaluates a single frozen point. For multistart precheck, recovery, "
        "and feasible search, hand off to Systems Mode with your current machine as baseline."
    ).classes("text-caption q-mb-sm")

    def _go_precheck() -> None:
        session.pd_pending_systems_action = "precheck"
        session.systems_workflow_step = "2 · Check & Solve"
        switch_deck("Systems Mode")
        ui.notify("Point Designer handoff — run Step ① precheck on Check & Solve.", type="info")

    ui.button(
        "Run Systems precheck (Systems Mode)",
        icon="hub",
        on_click=_go_precheck,
    ).props("outline").classes("w-full")
