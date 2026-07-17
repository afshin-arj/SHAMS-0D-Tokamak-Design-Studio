"""Trade Study Studio setup orientation."""
from __future__ import annotations

from nicegui import ui

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def render_setup_panel(*, default_open: bool = True) -> None:
    with ui.expansion("Trade study contract", icon="school", value=default_open).classes("w-full"):
        ui.markdown(
            "**What this mode does**\n"
            "- Budgeted LHS trade studies over explicit knob sets\n"
            "- Pareto fronts **only over feasible** sampled points\n"
            "- Study capsules for cross-deck handoff\n\n"
            "**What this mode does not do**\n"
            "- Modify frozen physics or use internal solvers\n"
            "- Claim a globally optimal machine\n"
            "- Smooth or relax constraints"
        )
        ui.markdown(
            "**Feasibility gate:** unified **governance** + **intent-aware blocking** "
            "(same policy as Point Designer). Pareto membership uses intent-feasible samples only."
        ).classes("text-caption q-mt-sm")
        ui.label("Knob sets (sampling domains)").classes("text-subtitle2 q-mt-sm")
        for ks in default_knob_sets()[:6]:
            ui.markdown(f"**{ks.name}** — {ks.notes}").classes("text-caption")
