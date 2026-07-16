"""Compare deck — load artifacts into slots A and B."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.compare_helpers import artifact_from_point, normalize_compare_artifact, slot_meta
from ui_nicegui.session import DesignSession


def render_setup_panel(session: DesignSession, *, on_change) -> None:
    meta_a = session.cmp_slot_a_meta or {}
    meta_b = session.cmp_slot_b_meta or {}
    have_a = isinstance(session.cmp_slot_a, dict)
    have_b = isinstance(session.cmp_slot_b, dict)

    ui.label("Baseline (A) vs variant (B)").classes("text-subtitle2")
    ui.label(
        "Slot A is typically baseline; Slot B is the scenario or design change you want to diagnose."
    ).classes("text-caption text-grey q-mb-sm")

    _, _, pd_out = get_point_artifact_triple(session)
    if isinstance(pd_out, dict) and pd_out:
        ui.label("Point Designer evaluation available — use Load buttons below.").classes(
            "text-caption text-positive q-mb-xs"
        )
    else:
        ui.label("No Point Designer evaluation yet — upload JSON or evaluate in Point Designer first.").classes(
            "text-caption text-grey q-mb-xs"
        )

    with ui.row().classes("w-full gap-4 items-start"):
        _slot_column(session, "A", meta_a, have_a, on_change)
        _slot_column(session, "B", meta_b, have_b, on_change)
        with ui.column().classes("flex-0 gap-2"):
            ui.button("Clear both", icon="clear", on_click=lambda: _clear_slots(session, on_change)).props("outline")
            ui.button("Swap A ↔ B", icon="swap_horiz", on_click=lambda: _swap_slots(session, on_change)).props("flat")

    with ui.expansion("Upload JSON artifacts", icon="upload").classes("w-full q-mt-sm"):
        async def _on_upload_a(e) -> None:
            await _store_upload(session, "A", e)
            on_change()

        async def _on_upload_b(e) -> None:
            await _store_upload(session, "B", e)
            on_change()

        with ui.row().classes("w-full gap-4"):
            ui.upload(label="Artifact A", auto_upload=True, on_upload=_on_upload_a).classes("flex-1")
            ui.upload(label="Artifact B", auto_upload=True, on_upload=_on_upload_b).classes("flex-1")

    ui.label(
        "Tip: Control Room **Scenario Delta** can send baseline/scenario pairs here via the Compare bridge."
    ).classes("text-caption text-grey q-mt-sm")


def _slot_column(session: DesignSession, slot: str, meta: dict, have: bool, on_change) -> None:
    is_a = slot == "A"
    with ui.column().classes("flex-1"):
        ui.checkbox(
            f"Use slot {slot}",
            value=session.cmp_use_slot_a if is_a else session.cmp_use_slot_b,
            on_change=lambda e, s=slot: (
                setattr(session, "cmp_use_slot_a" if s == "A" else "cmp_use_slot_b", bool(e.value)),
                on_change(),
            ),
        )
        if have:
            ui.label(
                f"{meta.get('label', 'loaded')} · hash {str(meta.get('inputs_hash', ''))[:8]}"
            ).classes("text-caption")
        else:
            ui.label("(empty — load from Point Designer or upload)").classes("text-caption text-grey")
        ui.button(
            f"Load Point Designer → {slot}",
            on_click=lambda s=slot: _load_pd_to_slot(session, s, on_change),
        ).props("flat dense outline")


def _load_pd_to_slot(session: DesignSession, slot: str, on_change) -> None:
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
    ui.notify(f"Loaded Point Designer into slot {slot}", type="positive")
    on_change()


def _clear_slots(session: DesignSession, on_change) -> None:
    session.cmp_slot_a = None
    session.cmp_slot_b = None
    session.cmp_slot_a_meta = {}
    session.cmp_slot_b_meta = {}
    session.cmp_use_slot_a = False
    session.cmp_use_slot_b = False
    ui.notify("Cleared Compare slots", type="info")
    on_change()


def _swap_slots(session: DesignSession, on_change) -> None:
    session.cmp_slot_a, session.cmp_slot_b = session.cmp_slot_b, session.cmp_slot_a
    session.cmp_slot_a_meta, session.cmp_slot_b_meta = (
        session.cmp_slot_b_meta,
        session.cmp_slot_a_meta,
    )
    session.cmp_use_slot_a, session.cmp_use_slot_b = (
        session.cmp_use_slot_b,
        session.cmp_use_slot_a,
    )
    ui.notify("Swapped slots A and B", type="info")
    on_change()


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
    ui.notify(f"Stored upload in slot {slot}", type="positive")


def resolve_artifacts(session: DesignSession) -> tuple[dict | None, dict | None]:
    art_a = session.cmp_slot_a if session.cmp_use_slot_a else None
    art_b = session.cmp_slot_b if session.cmp_use_slot_b else None
    return (
        normalize_compare_artifact(art_a) if isinstance(art_a, dict) else None,
        normalize_compare_artifact(art_b) if isinstance(art_b, dict) else None,
    )
