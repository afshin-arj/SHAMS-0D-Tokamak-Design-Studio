"""Pareto Lab setup orientation — contract and sampling scope."""
from __future__ import annotations

import json

from nicegui import ui

from ui.pareto_language import PARETO_OPTIMAL_DEF, TRUST_BOUNDARIES
from ui_nicegui.lib.pareto_interpret_helpers import governance_doc_paths, restore_pareto_artifact


def render_setup_panel(*, default_open: bool = True, on_restore=None) -> None:
    with ui.expansion("Sampling contract (read once)", icon="school", value=default_open).classes("w-full"):
        ui.markdown(PARETO_OPTIMAL_DEF)
        ui.label("Trust boundaries").classes("text-subtitle2 q-mt-sm")
        for line in TRUST_BOUNDARIES:
            ui.label(line).classes("text-caption")
        ui.markdown(
            "**Intent-gate (blocking):** unified **governance** hard constraints + **intent-aware blocking** "
            "(same policy as Point Designer Constraints tab) — screening; **not L0 FEASIBLE**. "
            "Research: only q95 blocks; TBR is ignored; "
            "engineering limits are diagnostic."
        ).classes("text-caption q-mt-sm")
        ui.markdown(
            "**Sampling hyper-rectangle:** R₀, Bt, Ip, fG, and optionally **Paux** — decision variables for LHS. "
            "Objectives are outputs evaluated by frozen truth."
        ).classes("text-caption")

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

    with ui.expansion("Replay artifact (audit mode)", icon="history").classes("w-full q-mt-sm"):
        ui.label("Load a prior Pareto JSON to reproduce the front without re-sampling.").classes("text-caption q-mb-sm")

        async def _upload_replay(e) -> None:
            try:
                payload = json.loads(e.content.read().decode("utf-8"))
                art = restore_pareto_artifact(payload)
                if on_restore:
                    on_restore(art)
                ui.notify("Pareto artifact restored for replay", type="positive")
            except Exception as exc:
                ui.notify(f"Replay failed: {exc}", type="negative")

        ui.upload(on_upload=_upload_replay).props('accept=".json" auto-upload label="Upload Pareto artifact"')
