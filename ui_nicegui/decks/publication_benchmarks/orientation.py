"""Publication pack orientation — what the batch run produces."""
from __future__ import annotations

from nicegui import ui


def render_pack_orientation(*, default_open: bool = True) -> None:
    with ui.expansion("What the publication pack does", icon="help", value=default_open).classes("w-full q-mb-sm"):
        ui.markdown(
            "Generates paper-ready benchmark tables and per-machine artifacts by evaluating "
            "configured reference machines with the **frozen Point Designer**. "
            "No physics, constraints, or policies are modified."
        )
        ui.label("Outputs include:").classes("text-subtitle2 q-mt-sm")
        ui.markdown(
            "- CSV benchmark tables (Research & Reactor)\n"
            "- Per-machine JSON artifacts (inputs, outputs, constraint ledger)\n"
            "- Run metadata (timestamp, version, hash)"
        )
        with ui.row().classes("w-full gap-4 q-mt-sm"):
            with ui.column().classes("flex-1"):
                ui.label("Research machines").classes("text-subtitle2")
                ui.label("Policy: Research intent · q95 hard · plant constraints diagnostic").classes("text-caption")
                ui.markdown("- ITER / JET / DIII-D / EAST / KSTAR / JT-60SA\n- SPARC / NSTX-U / MAST-U")
            with ui.column().classes("flex-1"):
                ui.label("Reactor & pilot plants").classes("text-subtitle2")
                ui.label("Policy: Reactor intent · full feasibility gates").classes("text-caption")
                ui.markdown("- ARC / ARIES-class\n- EU DEMO · STEP prototype (as configured)")
        ui.label("Every run is replayable. Every table is traceable.").classes("text-caption text-grey q-mt-sm")
