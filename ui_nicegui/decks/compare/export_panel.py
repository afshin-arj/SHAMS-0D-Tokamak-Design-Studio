"""Compare deck — export markdown and JSON bundles."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.compare_helpers import comparison_json_bundle, comparison_markdown


def render_export_panel(art_a: dict, art_b: dict) -> None:
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
