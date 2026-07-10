"""Regulatory & reviewer evidence pack panel."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    artifact_snapshot,
    build_regulatory_reviewer_pack,
    pick_session_run_artifact,
    validate_regulatory_pack_bytes,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

PACK_CONTENTS = (
    "- `artifact.json`: full run artifact\n"
    "- `dominance.json`: authority dominance snapshot\n"
    "- `assumptions.json`: scope + contract hashes\n"
    "- `narrative.md`: deterministic narrative header\n"
    "- `tables/constraints_*.csv`: constraint tables (when present)\n"
    "- `report/reviewer_summary.pdf`: PDF summary (when reportlab available)\n"
    "- `PACK_MANIFEST.json`: manifest + per-file SHA-256"
)


def render_regulatory_reviewer_pack(session: DesignSession) -> None:
    ui.label("Regulatory & reviewer evidence pack").classes("text-subtitle2")
    ui.label(
        "Licensing-grade deterministic ZIP with pack validator. Read-only; does not affect truth."
    ).classes("text-caption text-grey q-mb-sm")

    art = pick_session_run_artifact(session)
    if not isinstance(art, dict):
        empty_state(
            "No session run artifact — evaluate in **Point Designer** or **Systems Mode** first.",
            kind="warn",
        )
        from ui_nicegui.lib.navigation import switch_deck

        with ui.row().classes("gap-2 q-mt-sm"):
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: switch_deck("Point Designer"),
            ).props("outline color=primary")
            ui.button(
                "Open Systems Mode",
                icon="hub",
                on_click=lambda: switch_deck("Systems Mode"),
            ).props("flat outline")
        return

    ui.label("Run snapshot").classes("text-caption")
    render_json_blob(artifact_snapshot(art))

    async def _gen() -> None:
        try:
            data = await run.io_bound(build_regulatory_reviewer_pack, session)
            session.pub_regulatory_zip_bytes = data
            session.pub_regulatory_validate = None
            ui.notify("Reviewer pack generated", type="positive")
            _actions.refresh()
        except Exception as exc:
            ui.notify(f"Reviewer pack failed: {exc}", type="negative")

    ui.button("Generate reviewer pack ZIP", icon="folder_zip", on_click=_gen).props("outline color=primary q-mt-sm")
    _actions(session)


@ui.refreshable
def _actions(session: DesignSession) -> None:
    data = session.pub_regulatory_zip_bytes

    async def _validate() -> None:
        if not data:
            return
        try:
            rep = await run.io_bound(validate_regulatory_pack_bytes, data)
            session.pub_regulatory_validate = rep
            ui.notify(
                "Validation OK" if rep.get("ok") else "Validation failed",
                type="positive" if rep.get("ok") else "negative",
            )
            _actions.refresh()
        except Exception as exc:
            ui.notify(f"Validation error: {exc}", type="negative")

    if isinstance(data, (bytes, bytearray)) and len(data) > 100:
        with ui.row().classes("gap-2 q-mt-sm"):
            ui.button(
                "Download reviewer pack",
                icon="download",
                on_click=lambda: ui.download(bytes(data), "reviewer_pack.zip"),
            ).props("outline")
            ui.button("Validate ZIP", icon="verified", on_click=_validate).props("flat")

    val = session.pub_regulatory_validate
    if isinstance(val, dict):
        ui.label("Validation: PASS" if val.get("ok") else "Validation: FAIL").classes(
            "text-caption " + ("text-positive" if val.get("ok") else "text-negative")
        )
        for w in val.get("warnings") or []:
            ui.label(f"Warning: {w}").classes("text-caption text-orange")
        for e in val.get("errors") or []:
            ui.label(f"Error: {e}").classes("text-caption text-negative")

    with ui.expansion("What this pack contains", icon="info").classes("w-full q-mt-sm"):
        ui.markdown(PACK_CONTENTS)
