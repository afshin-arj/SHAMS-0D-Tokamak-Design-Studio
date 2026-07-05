"""Capsules panel — import/export/replay/diff (Phase 14)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.forge_machine_finder_helpers import (
    build_capsule_zip_bytes,
    diff_capsule_json,
    parse_capsule_upload,
    restore_workbench_from_capsule,
)
from ui_nicegui.session import DesignSession


def render_capsules(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Run Capsules").classes("text-subtitle1")
    ui.label(
        "Import/export Optimization Run Capsules (v2). Metadata replay only — truth remains the frozen evaluator."
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


async def _handle_restore(session: DesignSession, e, on_complete: Optional[Callable[[], None]]) -> None:
    try:
        content = e.content.read()
        capsule = await run.io_bound(parse_capsule_upload, content, e.name or "capsule.json")
        run_rep = restore_workbench_from_capsule(capsule)
        session.forge_workbench_run = run_rep
        session.forge_lens_contract = capsule.get("lens") if isinstance(capsule.get("lens"), dict) else None
        ui.notify("Capsule restored into workbench", type="positive")
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
        ui.json(d)


def _render_export(session: DesignSession) -> None:
    run_rep = session.forge_workbench_run
    if not isinstance(run_rep, dict) or run_rep.get("archive") is None:
        ui.label("Run Machine Finder or restore a capsule to enable export.").classes("text-caption text-grey")
        return

    with ui.expansion("Export capsule zip (v2)", icon="download").classes("w-full"):
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
