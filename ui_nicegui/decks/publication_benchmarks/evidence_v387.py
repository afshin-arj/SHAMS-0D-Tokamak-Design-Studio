"""Evidence Export — session cache ZIP (hash-locked, export-only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.pub_benchmark_extended_helpers import build_evidence_pack_v387, session_cache_sources
from ui_nicegui.lib.pub_helpers import evidence_source_label
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_evidence_pack_v387(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Evidence Export").classes("text-h6")
    ui.label(
        "Deterministic, hash-locked evidence ZIP from cached runs (export-only). "
        "Does not recompute physics. Distinct from Tab 4 reviewer/licensing packs."
    ).classes("text-caption q-mb-sm")

    cache = session_cache_sources(session)
    if not session.pub_v387_include:
        session.pub_v387_include = {
            k: isinstance(v, (dict, list)) for k, v in sorted(cache.items())
        }

    any_avail = any(isinstance(v, (dict, list)) for v in cache.values())
    if not any_avail:
        empty_state(
            "No cached session sources yet — evaluate in Point Designer, Scan Lab, or Pareto Lab first.",
            kind="warn",
        )
        with ui.row().classes("gap-2 q-mb-sm"):
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: switch_deck("Point Designer"),
            ).props("outline color=primary")

    ui.label("Select cached sources").classes("text-subtitle2")
    toggles: dict = {}

    with ui.row().classes("w-full gap-4 wrap"):
        for key in sorted(cache.keys()):
            avail = isinstance(cache.get(key), (dict, list))
            label = evidence_source_label(key)
            toggles[key] = ui.checkbox(
                f"{label}{'' if avail else ' (missing)'}",
                value=bool(session.pub_v387_include.get(key, avail)),
            ).props("disable" if not avail else "")

    notes = ui.textarea(
        "Reviewer notes (optional)",
        value=session.pub_v387_notes or "",
    ).classes("w-full").props("rows=4")

    async def _build() -> None:
        from ui_nicegui.lib.pub_helpers import PUB_RUNLOCK_OWNER, release_pub_lock, try_acquire_pub_lock
        from ui_nicegui.lib.helm_helpers import log_ui_event

        include = {k: bool(cb.value) for k, cb in toggles.items()}
        session.pub_v387_include = include
        session.pub_v387_notes = str(notes.value or "")
        if not try_acquire_pub_lock(session, "Publication Benchmarks: Evidence ZIP"):
            return
        log_ui_event(session, PUB_RUNLOCK_OWNER, "EvidencePackStart", {})
        version = "unknown"
        try:
            version = (Path(repo_root()) / "VERSION").read_text(encoding="utf-8").strip().splitlines()[0]
        except Exception:
            pass
        out_dir = Path(repo_root()) / "ui_runs" / "evidence_packs_v387"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_zip = out_dir / "evidence_pack.zip"
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
            log_ui_event(session, PUB_RUNLOCK_OWNER, "EvidencePackComplete", {})
            ui.notify("Evidence pack ZIP ready", type="positive")
            if on_complete:
                on_complete()
            _dl.refresh()
        except Exception as exc:
            ui.notify(f"Evidence pack failed: {exc}", type="negative")
        finally:
            release_pub_lock(session)

    ui.button("Build Evidence Pack", icon="folder_zip", on_click=_build, color="primary")
    _dl(session)


@ui.refreshable
def _dl(session: DesignSession) -> None:
    idx = session.pub_v387_last_index
    data = session.pub_v387_last_bytes
    if isinstance(idx, dict):
        with ui.expansion("Pack index", icon="list").classes("w-full q-mt-sm"):
            render_json_blob(idx)
    if isinstance(data, (bytes, bytearray)) and data:
        ui.button(
            "Download evidence pack ZIP",
            icon="download",
            on_click=lambda: ui.download(bytes(data), "evidence_pack.zip"),
        ).props("outline color=primary q-mt-sm")
