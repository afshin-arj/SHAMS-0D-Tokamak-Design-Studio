"""Forge setup orientation panel."""
from __future__ import annotations

from nicegui import ui


def render_setup_panel(*, default_open: bool = True) -> None:
    with ui.expansion("Forge contract (read once)", icon="school", value=default_open).classes("w-full"):
        ui.markdown(
            "**What this mode does**\n"
            "- Compiles reactor intent → candidate PointInputs (Intent Compiler)\n"
            "- Runs hybrid Machine Finder (global → surrogate → local refinement)\n"
            "- Builds candidate archives, resistance reports, and run capsules\n\n"
            "**What this mode does not do**\n"
            "- Modify frozen evaluator truth or relax constraints silently\n"
            "- Auto-apply candidates — promotion is always explicit\n"
            "- Guarantee feasibility — NO-SOLUTION is valid"
        )
        ui.markdown(
            "**Expert workflow:** Compile → Search → Workbench inspect → Export capsule → "
            "Promote to Point Designer → Re-evaluate with frozen truth."
        ).classes("text-caption q-mt-sm")
