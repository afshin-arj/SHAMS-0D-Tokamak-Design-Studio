"""Opt Lab deck — certified-search entry surface (Certified Optimizer 1.1).

Thin hub: three-step path + honesty copy + routes into Systems Mode,
Pareto Lab, and Control Room Certified Search. SearchDrivers, run stamps,
and warm-start are later tickets — this deck does not claim an authoritative optimum.
"""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.components.opt_lab_entry_panel import render_opt_lab_entry
from ui_nicegui.lib.opt_lab_entry import OPT_LAB_DECK, OPT_LAB_TAGLINE
from ui_nicegui.session import DesignSession


def render_opt_lab(session: DesignSession) -> None:
    ui.label(OPT_LAB_DECK).classes("text-h5")
    ui.label(OPT_LAB_TAGLINE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("opt_lab", default_open=False)
    render_opt_lab_entry(session)

    with ui.expansion("Coming next in Opt Lab", icon="schedule", value=False).classes(
        "w-full q-mt-md"
    ):
        ui.markdown(
            "- **Run stamp** — VERSION + ObjectiveContract hash + seed on every opt run\n"
            "- **Honesty polish** — VERIFIED / REJECTED + atlas tooltips on results viewers\n"
            "- **Champion warm-start** — one-click seed from champion PointInputs\n"
            "- **SearchDrivers** — SLSQP / NSGA propose-only (still certified by CCFS)\n\n"
            "Until then, use the routes above — every path still proposes only and "
            "re-evaluates through frozen truth."
        ).classes("text-caption")
