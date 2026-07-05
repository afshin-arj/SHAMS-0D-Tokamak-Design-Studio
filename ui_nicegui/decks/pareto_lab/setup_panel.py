"""Pareto Lab setup orientation — contract and sampling scope."""
from __future__ import annotations

from nicegui import ui

from ui.pareto_language import PARETO_OPTIMAL_DEF, TRUST_BOUNDARIES
from ui_nicegui.lib.pareto_interpret_helpers import governance_doc_paths


def render_setup_panel(*, default_open: bool = True) -> None:
    with ui.expansion("Sampling contract (read once)", icon="school", value=default_open).classes("w-full"):
        ui.markdown(PARETO_OPTIMAL_DEF)
        ui.label("Trust boundaries").classes("text-subtitle2 q-mt-sm")
        for line in TRUST_BOUNDARIES:
            ui.label(line).classes("text-caption")
        ui.markdown(
            "**Sampling hyper-rectangle:** R0, Bt, Ip, fG only — decision variables for LHS. "
            "Objectives are outputs evaluated by frozen truth."
        ).classes("text-caption q-mt-sm")

        docs = governance_doc_paths()
        if docs:
            ui.label("Governance documents (read-only)").classes("text-subtitle2 q-mt-sm")
            with ui.row().classes("gap-2 flex-wrap"):
                for fn, text in docs.items():
                    ui.button(
                        f"Download {fn}",
                        icon="download",
                        on_click=lambda t=text, f=fn: ui.download(t.encode("utf-8"), f),
                    ).props("flat outline dense")
