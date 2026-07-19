"""Opt Lab deck — certified-search entry surface (Certified Optimizer 1.1–3.1).

Thin hub: three-step path + honesty copy + champion warm-start + routes into
Systems Mode, Pareto Lab, and Control Room Certified Search. SearchDrivers
propose only; SLSQP neighborhood and NSGA-II fronts re-certify via CCFS.
This deck does not claim an authoritative optimum.
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
            "- **SLSQP SearchDriver** — propose-only continuous FoM search "
            "(best + neighborhood always re-certified by CCFS)\n"
            "- **NSGA-II SearchDriver** — propose-only multi-objective front "
            "(feasible-first; CCFS-certify shortlist; atlas dominatees next)\n"
            "- **Pareto Lab unify** — one certified-front viewer (Phase 3.3)\n\n"
            "Champion warm-start, run stamps, honesty copy, and neighborhood "
            "re-certify hooks are on this hub. Every path still proposes only "
            "and re-evaluates through frozen truth."
        ).classes("text-caption")
