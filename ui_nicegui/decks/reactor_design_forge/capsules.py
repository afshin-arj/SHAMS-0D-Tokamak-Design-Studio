"""Capsules panel — import/export/replay/diff."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.decks.reactor_design_forge.handoff_panel import render_archive_handoffs
from ui_nicegui.lib.forge_interpret_helpers import design_card_markdown
from ui_nicegui.lib.forge_machine_finder_helpers import (
    build_capsule_zip_bytes,
    build_forge_audit_pack_zip,
    diff_capsule_json,
    parse_capsule_upload,
    restore_workbench_from_capsule,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_capsules(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Run Capsules").classes("text-subtitle1")
    ui.label(
        "Import and export optimization run capsules. Metadata replay only — truth remains the frozen evaluator."
    ).classes("text-caption text-grey q-mb-sm")

    with ui.expansion("Restore capsule", icon="upload").classes("w-full q-mb-sm"):
        ui.upload(on_upload=lambda e: _handle_restore(session, e, on_complete)).props(
            'accept=".zip,.json" auto-upload'
        ).classes("w-full")

    with ui.expansion("Diff two capsules (JSON)", icon="compare").classes("w-full q-mb-sm"):
        ui.upload(
            label="Capsule A (JSON)",
            on_upload=lambda e: _handle_diff_upload(session, e, slot="a"),
        ).props('accept=".json" auto-upload').classes("w-full")
        ui.upload(
            label="Capsule B (JSON)",
            on_upload=lambda e: _handle_diff_upload(session, e, slot="b"),
        ).props('accept=".json" auto-upload').classes("w-full")

        async def _run_diff() -> None:
            a = session.forge_capsule_diff_a
            b = session.forge_capsule_diff_b
            if not isinstance(a, dict) or not isinstance(b, dict):
                ui.notify("Upload both capsule JSON files first", type="warning")
                return
            try:
                session.forge_capsule_diff = await run.io_bound(diff_capsule_json, a, b)
                ui.notify("Diff complete", type="positive")
                _diff_view.refresh()
            except Exception as exc:
                ui.notify(f"Diff failed: {exc}", type="negative")

        ui.button("Compute diff", icon="compare", on_click=_run_diff).props("outline")
        _diff_view(session)

    _render_export(session)

    ui.separator().classes("q-my-sm")
    run_rep = session.forge_workbench_run
    if isinstance(run_rep, dict):
        render_archive_handoffs(session, run_rep, on_complete=on_complete)

        archive = run_rep.get("archive") or []
        if archive:
            ui.label("Design card (markdown)").classes("text-subtitle2 q-mt-md")
            row_n = ui.number("Row for design card", value=0, min=0, max=max(len(archive) - 1, 0), step=1)
            intent = str(run_rep.get("intent") or session.forge_mf_intent_label)

            def _dl_card() -> None:
                i = int(row_n.value or 0)
                cand = archive[i] if 0 <= i < len(archive) else {}
                md = design_card_markdown(cand if isinstance(cand, dict) else {}, intent)
                if md:
                    ui.download(md.encode("utf-8"), f"forge_design_card_{i}.md")
                else:
                    ui.notify("Design card unavailable for this row", type="warning")

            ui.button("Download design card", icon="description", on_click=_dl_card).props("flat outline")


async def _handle_restore(session: DesignSession, e, on_complete: Optional[Callable[[], None]]) -> None:
    try:
        content = e.content.read()
        capsule = await run.io_bound(parse_capsule_upload, content, e.name or "capsule.json")
        run_rep = restore_workbench_from_capsule(capsule)
        session.forge_workbench_run = run_rep
        session.forge_lens_contract = capsule.get("lens") if isinstance(capsule.get("lens"), dict) else None
        session.forge_workflow_step = "3 · Workbench"
        session.forge_deck = "Machine Finder"
        ui.notify("Capsule restored — open **Workbench** tab if not already there.", type="positive")
        if on_complete:
            on_complete()
    except Exception as exc:
        ui.notify(f"Restore failed: {exc}", type="negative")


async def _handle_diff_upload(session: DesignSession, e, *, slot: str) -> None:
    try:
        import json

        obj = json.loads(e.content.read().decode("utf-8"))
        if slot == "a":
            session.forge_capsule_diff_a = obj
        else:
            session.forge_capsule_diff_b = obj
        ui.notify(f"Capsule {slot.upper()} loaded", type="info")
    except Exception as exc:
        ui.notify(f"Upload failed: {exc}", type="negative")


@ui.refreshable
def _diff_view(session: DesignSession) -> None:
    d = session.forge_capsule_diff
    if isinstance(d, dict):
        render_json_blob(d)


def _render_export(session: DesignSession) -> None:
    run_rep = session.forge_workbench_run
    if not isinstance(run_rep, dict) or run_rep.get("archive") is None:
        ui.label("Run Machine Finder or restore a capsule to enable export.").classes("text-caption text-grey")
        return

    with ui.expansion("Export capsule zip", icon="download").classes("w-full"):
        ui.label("Builds run_capsule.json + archive snapshot + optional resistance report.").classes("text-caption")

        async def _build_zip() -> None:
            ui.notify("Building capsule zip…", type="info")
            try:
                bounds = session.forge_mf_last_bounds or {}
                lens = session.forge_lens_contract or {}
                data, name = await run.io_bound(
                    build_capsule_zip_bytes,
                    run_rep,
                    lens_contract=lens,
                    bounds=bounds,
                )
                session.forge_capsule_zip_bytes = data
                session.forge_capsule_zip_name = name
                ui.notify("Capsule zip ready", type="positive")
                _export_btn.refresh()
            except Exception as exc:
                ui.notify(f"Export failed: {exc}", type="negative")

        ui.button("Build capsule zip", icon="archive", on_click=_build_zip).props("outline")
        _export_btn(session)

    archive = run_rep.get("archive") or []
    with ui.expansion("Audit Pack (narrative + reviewer + capsule)", icon="folder_zip").classes("w-full q-mt-sm"):
        ui.label(
            "Single ZIP: report narrative, design card, nested reviewer packet, and run capsule — "
            "reviewer-room ready."
        ).classes("text-caption q-mb-sm")
        row_ap = ui.number(
            "Archive row #",
            value=0,
            min=0,
            max=max(len(archive) - 1, 0) if archive else 0,
            step=1,
        )

        async def _build_audit_pack() -> None:
            if not archive:
                ui.notify("No archive rows available", type="warning")
                return
            ui.notify("Building Forge Audit Pack…", type="info")
            try:
                bounds = session.forge_mf_last_bounds or {}
                lens = session.forge_lens_contract or {}
                intent = str(run_rep.get("intent") or session.forge_mf_intent_label)
                data, name = await run.io_bound(
                    build_forge_audit_pack_zip,
                    run_rep,
                    row_idx=int(row_ap.value or 0),
                    lens_contract=lens,
                    bounds=bounds,
                    intent=intent,
                )
                session.forge_audit_pack_bytes = data
                session.forge_audit_pack_name = name
                ui.notify("Audit Pack ready", type="positive")
                _audit_pack_btn.refresh()
            except Exception as exc:
                ui.notify(f"Audit Pack failed: {exc}", type="negative")

        ui.button("Build Audit Pack", icon="inventory_2", on_click=_build_audit_pack).props("outline color=primary")
        _audit_pack_btn(session)


@ui.refreshable
def _audit_pack_btn(session: DesignSession) -> None:
    data = getattr(session, "forge_audit_pack_bytes", None)
    if isinstance(data, (bytes, bytearray)) and len(data) > 100:
        ui.button(
            "Download Audit Pack",
            icon="download",
            on_click=lambda: ui.download(
                bytes(data),
                getattr(session, "forge_audit_pack_name", None) or "shams_forge_audit_pack.zip",
            ),
        ).props("color=primary flat q-mt-sm")


@ui.refreshable
def _export_btn(session: DesignSession) -> None:
    data = session.forge_capsule_zip_bytes
    if isinstance(data, (bytes, bytearray)) and len(data) > 100:
        ui.button(
            "Download capsule zip",
            icon="download",
            on_click=lambda: ui.download(
                bytes(data),
                session.forge_capsule_zip_name or "opt_capsule.zip",
            ),
        ).props("color=primary flat q-mt-sm")
