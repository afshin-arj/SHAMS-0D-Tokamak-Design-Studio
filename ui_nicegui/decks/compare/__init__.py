"""Compare deck — NiceGUI Batch 8.

Side-by-side artifact comparison from session slots or Point Designer handoff.
"""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.compare import results, verdict
from ui_nicegui.lib.compare_helpers import (
    artifact_from_point,
    normalize_compare_artifact,
    slot_meta,
    summarize_comparison,
)
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.session import DesignSession


def _refresh() -> None:
    _render_verdict.refresh()
    _render_comparison.refresh()


def render_compare(session: DesignSession) -> None:
    ui.label("Compare").classes("text-h5")
    ui.label(
        "Side-by-side artifact comparison to isolate mechanism and constraint-margin deltas."
    ).classes("text-caption text-grey q-mb-sm")

    ui.label("Compare sources").classes("text-subtitle2")
    ui.label("Use session slots (recommended) or upload JSON artifacts.").classes("text-caption q-mb-sm")

    _render_slot_controls(session)
    ui.separator()
    _render_verdict(session)
    _render_comparison(session)


def _render_slot_controls(session: DesignSession) -> None:
    meta_a = session.cmp_slot_a_meta or {}
    meta_b = session.cmp_slot_b_meta or {}
    have_a = isinstance(session.cmp_slot_a, dict)
    have_b = isinstance(session.cmp_slot_b, dict)

    with ui.row().classes("w-full gap-4 items-start"):
        with ui.column().classes("flex-1"):
            ui.checkbox(
                "Use session Slot A",
                value=session.cmp_use_slot_a,
                on_change=lambda e: setattr(session, "cmp_use_slot_a", bool(e.value)),
            )
            if have_a:
                ui.label(
                    f"Slot A: {meta_a.get('label', '')} | {str(meta_a.get('inputs_hash', ''))[:8]}"
                ).classes("text-caption")
            else:
                ui.label("Slot A: (empty)").classes("text-caption text-grey")
            ui.button(
                "Load Point Designer → A",
                on_click=lambda: _load_pd_to_slot(session, "A"),
            ).props("flat dense outline")
        with ui.column().classes("flex-1"):
            ui.checkbox(
                "Use session Slot B",
                value=session.cmp_use_slot_b,
                on_change=lambda e: setattr(session, "cmp_use_slot_b", bool(e.value)),
            )
            if have_b:
                ui.label(
                    f"Slot B: {meta_b.get('label', '')} | {str(meta_b.get('inputs_hash', ''))[:8]}"
                ).classes("text-caption")
            else:
                ui.label("Slot B: (empty)").classes("text-caption text-grey")
            ui.button(
                "Load Point Designer → B",
                on_click=lambda: _load_pd_to_slot(session, "B"),
            ).props("flat dense outline")
        with ui.column().classes("flex-0"):
            ui.button("Clear slots", icon="clear", on_click=lambda: _clear_slots(session)).props("outline")

    with ui.expansion("Upload artifacts (JSON)", icon="upload").classes("w-full q-mt-sm"):
        async def _on_upload_a(e) -> None:
            await _store_upload(session, "A", e)
            _refresh()

        async def _on_upload_b(e) -> None:
            await _store_upload(session, "B", e)
            _refresh()

        with ui.row().classes("w-full gap-4"):
            ui.upload(label="Artifact A", auto_upload=True, on_upload=_on_upload_a).classes("flex-1")
            ui.upload(label="Artifact B", auto_upload=True, on_upload=_on_upload_b).classes("flex-1")


def _load_pd_to_slot(session: DesignSession, slot: str) -> None:
    art = artifact_from_point(session)
    if not art:
        ui.notify("No Point Designer evaluation available", type="warning")
        return
    if slot == "A":
        session.cmp_slot_a = art
        session.cmp_slot_a_meta = slot_meta(art, label="Point Designer")
        session.cmp_use_slot_a = True
    else:
        session.cmp_slot_b = art
        session.cmp_slot_b_meta = slot_meta(art, label="Point Designer")
        session.cmp_use_slot_b = True
    ui.notify(f"Loaded Point Designer artifact into Slot {slot}", type="positive")
    _refresh()


def _clear_slots(session: DesignSession) -> None:
    session.cmp_slot_a = None
    session.cmp_slot_b = None
    session.cmp_slot_a_meta = {}
    session.cmp_slot_b_meta = {}
    ui.notify("Cleared Compare slots", type="info")
    _refresh()


async def _store_upload(session: DesignSession, slot: str, e) -> None:
    try:
        content = e.content.read()
        art = json.loads(content.decode("utf-8") if isinstance(content, bytes) else content)
    except Exception as exc:
        ui.notify(f"Invalid JSON upload: {exc}", type="negative")
        return
    norm = normalize_compare_artifact(art)
    if slot == "A":
        session.cmp_slot_a = norm
        session.cmp_slot_a_meta = slot_meta(norm, label="Uploaded")
        session.cmp_use_slot_a = True
    else:
        session.cmp_slot_b = norm
        session.cmp_slot_b_meta = slot_meta(norm, label="Uploaded")
        session.cmp_use_slot_b = True
    ui.notify(f"Stored upload in Slot {slot}", type="positive")


def _resolve_artifacts(session: DesignSession) -> tuple[dict | None, dict | None]:
    art_a = session.cmp_slot_a if session.cmp_use_slot_a else None
    art_b = session.cmp_slot_b if session.cmp_use_slot_b else None
    return (
        normalize_compare_artifact(art_a) if isinstance(art_a, dict) else None,
        normalize_compare_artifact(art_b) if isinstance(art_b, dict) else None,
    )


@ui.refreshable
def _render_verdict(session: DesignSession) -> None:
    art_a, art_b = _resolve_artifacts(session)
    if art_a and art_b:
        summary = summarize_comparison(art_a, art_b)
    else:
        summary = None
        if session.cmp_use_slot_a and not session.cmp_slot_a:
            empty_state("Slot A is selected but empty.", kind="warn")
        if session.cmp_use_slot_b and not session.cmp_slot_b:
            empty_state("Slot B is selected but empty.", kind="warn")
    verdict.render_compare_verdict(summary)


@ui.refreshable
def _render_comparison(session: DesignSession) -> None:
    art_a, art_b = _resolve_artifacts(session)
    if not (art_a and art_b):
        _, _, point_out = get_point_artifact_triple(session)
        if not isinstance(point_out, dict):
            empty_state(
                "Run **Point Designer** and load artifacts into slots A/B to compare.",
                kind="info",
            )
        return
    ui.separator()
    results.render_comparison_results(art_a, art_b)
