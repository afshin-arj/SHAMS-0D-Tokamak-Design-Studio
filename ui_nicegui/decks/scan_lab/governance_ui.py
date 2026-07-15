"""Scan Lab governance — no-optimization contract and Systems Mode handoff."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.scan_labels import NO_OPTIMIZATION_NOTICE, SLICE_MITIGATION
from ui_nicegui.lib.scan_workbench_helpers import probe_promote_inputs
from ui_nicegui.session import DesignSession


def render_governance_panel(session: DesignSession, rep: dict | None = None) -> None:
    with ui.expansion("Governance: map vs optimize", icon="policy", value=session.scan_teaching_mode).classes(
        "w-full q-mb-sm"
    ):
        ui.markdown(NO_OPTIMIZATION_NOTICE).classes("text-caption q-mb-xs")
        ui.markdown(SLICE_MITIGATION).classes("text-caption text-grey q-mb-sm")

        def _systems() -> None:
            if isinstance(rep, dict):
                from ui_nicegui.lib.scan_workbench_helpers import build_point_grid

                grid = build_point_grid(rep)
                cell = grid.get((int(session.scan_wb_i), int(session.scan_wb_j)))
                if cell:
                    cand = probe_promote_inputs(rep, cell)
                    session.systems_inputs_overrides = {
                        k: float(v) for k, v in cand.items() if isinstance(v, (int, float))
                    }
            session.systems_workflow_step = "1 · Targets"
            switch_deck("Systems Mode", force=True)
            ui.notify("Opened Systems Mode — configure targets and run precheck/solve.", type="info")

        ui.button("Need target matching? → Systems Mode", icon="hub", on_click=_systems).props("outline flat")
