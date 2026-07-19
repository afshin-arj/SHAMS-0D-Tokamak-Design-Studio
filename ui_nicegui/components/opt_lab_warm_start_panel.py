"""Reusable champion warm-start control (Opt Lab / Systems Mode / Pareto Lab).

Propose-only: loads champion PointInputs as a search seed; never evaluates or
claims a certified optimum.
"""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.opt_lab_warm_start import (
    WARM_START_HONESTY,
    WARM_START_TAGLINE,
    WARM_START_TITLE,
    apply_champion_warm_start,
    warm_start_summary,
)
from ui_nicegui.lib.studio_entry import champion_template_options
from ui_nicegui.session import DesignSession


def render_champion_warm_start(
    session: DesignSession,
    *,
    on_loaded: Optional[Callable[[], None]] = None,
    compact: bool = False,
) -> None:
    """Render one-click champion → search-seed control."""
    options = champion_template_options()
    labels = {o["case_id"]: o["label"] for o in options}
    stories = {o["case_id"]: o["story"] for o in options}
    default_id = getattr(session, "opt_lab_warm_start_case_id", None)
    if default_id not in labels and options:
        default_id = options[0]["case_id"]

    card = ui.card().classes("w-full q-mb-sm").props("flat bordered")
    with card:
        ui.label(WARM_START_TITLE).classes("text-subtitle2" if compact else "text-h6")
        ui.label(WARM_START_TAGLINE).classes("text-caption text-grey q-mb-xs")
        ui.label(WARM_START_HONESTY).classes("text-caption text-orange q-mb-sm")
        status = ui.label(warm_start_summary(session)).classes("text-caption text-grey q-mb-sm")

        with ui.row().classes("w-full items-end gap-3 flex-wrap"):
            sel = ui.select(
                labels,
                label="Champion case (search seed)",
                value=default_id,
            ).classes("col-grow")
            story = ui.label(
                stories.get(str(default_id), "") if default_id else ""
            ).classes("text-caption text-grey col-12")

            def _on_sel() -> None:
                story.set_text(stories.get(str(sel.value), ""))

            sel.on("update:model-value", lambda: _on_sel())

            def _load() -> None:
                if not sel.value:
                    ui.notify("Select a champion case first.", type="warning")
                    return
                try:
                    meta = apply_champion_warm_start(session, str(sel.value))
                except KeyError as exc:
                    ui.notify(str(exc), type="negative")
                    return
                status.set_text(warm_start_summary(session))
                ui.notify(
                    f"Search seed loaded: {meta.get('label')} "
                    f"({meta.get('override_count')} inputs). "
                    "Propose-only — Evaluate / Certify / Run still required.",
                    type="positive",
                )
                if on_loaded:
                    on_loaded()

            ui.button(
                "Load as search seed",
                icon="bolt",
                on_click=_load,
            ).props("color=primary outline" if compact else "color=primary")
