"""Verdict hero strip for Point Designer (NiceGUI)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def render_hero(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not out:
        empty_state("No evaluation loaded. Click **Evaluate Point** in Configure.", kind="info")
        return
    summary = verdict_summary(out)
    verdict_banner(summary["verdict"], detail=f"Dominant: {summary['dominant']}")
    kpi_row([
        ("Performance", summary["q_label"]),
        ("Triple product proxy", summary["nt_label"]),
        ("Pipeline parity", "aligned" if summary.get("parity_aligned") else "mismatch"),
    ])
    subs = summary.get("subsystems") or {}
    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        for name in ("magnets", "exhaust", "neutronics", "control", "transport", "plant"):
            status = subs.get(name, "pass")
            color = {"pass": "green", "fail": "red", "warn": "orange"}.get(status, "grey")
            ui.badge(name.replace("_", " ").title(), color=color).props("outline")
