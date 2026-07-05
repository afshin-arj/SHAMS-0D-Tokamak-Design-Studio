"""Regulatory Evidence Pack Builder v387."""
from __future__ import annotations

import json
from pathlib import Path

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.lib.pub_benchmark_extended_helpers import build_evidence_pack_v387, session_cache_sources
from ui_nicegui.session import DesignSession


def render_evidence_pack_v387(session: DesignSession) -> None:
    ui.label("Regulatory Evidence Pack Builder").classes("text-h6")
    ui.label(
        "Deterministic, hash-locked evidence ZIP from cached runs (export-only). "
        "Does not recompute physics."
    ).classes("text-caption q-mb-sm")

    cache = session_cache_sources(session)
    if not session.pub_v387_include:
        session.pub_v387_include = {
            k: isinstance(v, (dict, list)) for k, v in sorted(cache.items())
        }

    ui.label("Select cached sources").classes("text-subtitle2")
    toggles: dict = {}

    with ui.row().classes("w-full gap-4 wrap"):
        for i, key in enumerate(sorted(cache.keys())):
            avail = isinstance(cache.get(key), (dict, list))
            toggles[key] = ui.checkbox(
                f"{key}{'' if avail else ' (missing)'}",
                value=bool(session.pub_v387_include.get(key, avail)),
            ).props("disable" if not avail else "")

    notes = ui.textarea(
        "Reviewer notes (optional)",
        value=session.pub_v387_notes or "",
    ).classes("w-full").props("rows=4")

    async def _build() -> None:
        include = {k: bool(cb.value) for k, cb in toggles.items()}
        session.pub_v387_include = include
        session.pub_v387_notes = str(notes.value or "")
        version = "unknown"
        try:
            version = (Path(repo_root()) / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
        except Exception:
            pass
        out_dir = Path(repo_root()) / "ui_runs" / "evidence_packs_v387"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_zip = out_dir / "evidence_pack_v387.zip"
        try:
            res = await run.io_bound(
                build_evidence_pack_v387,
                out_zip,
                shams_version=version,
                sources=cache,
                include=include,
                notes=session.pub_v387_notes,
            )
            session.pub_v387_last_index = res.index
            session.pub_v387_last_bytes = res.zip_bytes
            ui.notify("Evidence pack ZIP ready", type="positive")
            _dl.refresh()
        except Exception as exc:
            ui.notify(f"Evidence pack failed: {exc}", type="negative")

    ui.button("Build Evidence Pack", icon="folder_zip", on_click=_build).props("color=primary outline")
    _dl(session)


@ui.refreshable
def _dl(session: DesignSession) -> None:
    idx = session.pub_v387_last_index
    data = session.pub_v387_last_bytes
    if isinstance(idx, dict):
        with ui.expansion("Pack index", icon="list_alt").classes("w-full q-mt-sm"):
            ui.json(idx)
    if isinstance(data, (bytes, bytearray)) and len(data) > 100:
        ui.button(
            "Download Evidence Pack (ZIP)",
            icon="download",
            on_click=lambda: ui.download(bytes(data), "evidence_pack_v387.zip"),
        ).props("outline")
