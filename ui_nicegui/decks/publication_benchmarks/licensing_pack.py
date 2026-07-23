"""Licensing evidence Tier 2 pack panel."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    artifact_snapshot,
    build_licensing_tier2_pack,
    pick_session_run_artifact,
    validate_licensing_pack_bytes,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

TIER2_CONTENTS = (
    "- `artifact.json`: full run artifact\n"
    "- `contract_registry.json`: governance contract registry snapshot\n"
    "- `authority_audit.json`: authority overlay audit trail\n"
    "- `replay_payload.json`: deterministic replay bundle\n"
    "- `PACK_MANIFEST.json`: manifest + per-file SHA-256"
)


def render_licensing_tier2_pack(session: DesignSession) -> None:
    ui.label("Licensing evidence Tier 2 (reviewer ZIP)").classes("text-subtitle2")
    ui.label(
        "Governance-strengthened deterministic ZIP for audit/review support — "
        "not a licensing determination. Validation checks ZIP integrity and pack structure only; "
        "read-only; does not affect frozen truth."
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

    render_json_blob(artifact_snapshot(art))

    async def _gen() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        if getattr(session, "pub_running", False):
            ui.notify("Publication job already running", type="warning")
            return
        locked, task, is_owner = runlock_status("PublicationBenchmarks")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Publication: Licensing Tier 2 pack", "PublicationBenchmarks"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        session.pub_running = True
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_status()
        refresh_helm()
        try:
            data = await run.io_bound(build_licensing_tier2_pack, session)
            session.pub_licensing_zip_bytes = data
            session.pub_licensing_validate = None
            ui.notify("Tier 2 reviewer pack generated (not a licensing determination)", type="positive")
            _actions.refresh()
        except Exception as exc:
            ui.notify(f"Licensing pack failed: {exc}", type="negative")
        finally:
            session.pub_running = False
            runlock_release("PublicationBenchmarks")
            refresh_status()
            refresh_helm()

    ui.button("Generate Tier 2 licensing pack", icon="folder_zip", on_click=_gen).props("outline q-mt-sm")
    _actions(session)


@ui.refreshable
def _actions(session: DesignSession) -> None:
    data = session.pub_licensing_zip_bytes

    async def _validate() -> None:
        if not data:
            return
        try:
            rep = await run.io_bound(validate_licensing_pack_bytes, data)
            session.pub_licensing_validate = rep
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
                "Download Tier 2 pack",
                icon="download",
                on_click=lambda: ui.download(bytes(data), "licensing_pack_tier2.zip"),
            ).props("outline")
            ui.button("Validate ZIP", icon="verified", on_click=_validate).props("flat")

    val = session.pub_licensing_validate
    if isinstance(val, dict):
        ui.label(
            "Pack integrity: PASS (not a licensing determination)"
            if val.get("ok")
            else "Pack integrity: FAIL"
        ).classes(
            "text-caption " + ("text-positive" if val.get("ok") else "text-negative")
        )
        ui.label(
            "Checks ZIP structure / hashes only — does not certify regulatory readiness."
        ).classes("text-caption text-grey")
        for w in val.get("warnings") or []:
            ui.label(f"Warning: {w}").classes("text-caption text-orange")
        for e in val.get("errors") or []:
            ui.label(f"Error: {e}").classes("text-caption text-negative")

    with ui.expansion("What Tier 2 contains", icon="info").classes("w-full q-mt-sm"):
        ui.markdown(TIER2_CONTENTS)
