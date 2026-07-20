"""Compare deck — export markdown and JSON bundles + outbound handoffs."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.compare_helpers import (
    apply_artifact_inputs,
    comparison_json_bundle,
    comparison_markdown,
)
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.session import DesignSession


def render_export_panel(session: DesignSession, art_a: dict, art_b: dict) -> None:
    ui.label("Export comparison").classes("text-subtitle2")
    ui.label(
        "Markdown for human review; JSON bundle for CI, Control Room, or archival replay."
    ).classes("text-caption text-grey q-mb-sm")

    md = comparison_markdown(art_a, art_b).encode("utf-8")
    bundle = json.dumps(comparison_json_bundle(art_a, art_b), indent=2, default=str).encode("utf-8")

    with ui.row().classes("gap-2"):
        ui.button(
            "Download markdown",
            icon="download",
            on_click=lambda: ui.download(md, "artifact_comparison.md"),
        ).props("outline")
        ui.button(
            "Download JSON bundle",
            icon="download",
            on_click=lambda: ui.download(bundle, "artifact_comparison.json"),
        ).props("outline color=primary")

    ui.separator().classes("q-my-sm")
    ui.label("Outbound handoffs").classes("text-subtitle2")
    ui.label(
        "Apply variant (B) or baseline (A) inputs to Point Designer for re-evaluation with frozen truth."
    ).classes("text-caption text-grey q-mb-sm")

    def _apply(slot_art: dict, label: str) -> None:
        n = apply_artifact_inputs(session, slot_art)
        if n:
            navigate_to_point_designer(session)
            ui.notify(
                f"Applied {n} input fields from slot {label} — KPIs marked STALE until Evaluate Point.",
                type="positive",
            )
        else:
            ui.notify(f"No overlapping inputs copied from slot {label}.", type="warning")

    with ui.row().classes("gap-2"):
        ui.button("Apply slot A → Point Designer", icon="input", on_click=lambda: _apply(art_a, "A")).props("outline")
        ui.button("Apply slot B → Point Designer", icon="input", on_click=lambda: _apply(art_b, "B")).props(
            "outline color=primary"
        )
