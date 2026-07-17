"""Studio entry panel — verdict-first landing card (Independence Phase 3.4).

Shown on the default landing deck (Point Designer) while no evaluation is
loaded. One-click champion templates, the three-step path to a certified
verdict, and onboarding doc links. Propose-only: nothing here evaluates.
"""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.studio_entry import (
    STUDIO_DOC_LINKS,
    STUDIO_ENTRY_TAGLINE,
    STUDIO_ENTRY_TITLE,
    STUDIO_NO_SOLUTION_NOTE,
    STUDIO_STEPS,
    STUDIO_WHAT_SHAMS_ANSWERS,
    apply_champion_template,
    champion_template_options,
)
from ui_nicegui.session import DesignSession


def _open_doc_in_docs_library(session: DesignSession, doc_rel_path: str) -> None:
    """Navigate to Control Room → Constitution → Docs Library with the doc preselected."""
    from ui_nicegui.lib.navigation import switch_deck

    doc_name = doc_rel_path.split("/")[-1]
    # Session wiring mirrors control_room/__init__.py section sync.
    session.cr_workflow_step = "2 · Constitution"
    session.cr_section = "Constitution"
    session.cr_const_tab = "Docs Library"
    session.cr_docs_sel = doc_name
    switch_deck("Control Room")
    ui.notify(f"Opened Docs Library: {doc_name}", type="info")


def render_studio_entry(session: DesignSession, *, on_loaded: Optional[Callable[[], None]] = None) -> None:
    with ui.card().classes("w-full q-mb-md").props("flat bordered"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(STUDIO_ENTRY_TITLE).classes("text-h6")
            ui.button(
                icon="close",
                on_click=lambda: _dismiss(session),
            ).props('flat round dense title="Hide this entry card for this session"')
        ui.label(STUDIO_ENTRY_TAGLINE).classes("text-body2 q-mb-sm")

        with ui.row().classes("w-full gap-6"):
            with ui.column().classes("flex-1"):
                ui.label("What SHAMS answers").classes("text-subtitle2")
                for line in STUDIO_WHAT_SHAMS_ANSWERS:
                    ui.label(f"• {line}").classes("text-caption")
                ui.label(STUDIO_NO_SOLUTION_NOTE).classes("text-caption text-orange q-mt-xs")
            with ui.column().classes("flex-1"):
                ui.label("Three steps to a certified verdict").classes("text-subtitle2")
                for idx, step in enumerate(STUDIO_STEPS, start=1):
                    ui.label(f"{idx}. {step}").classes("text-caption")
                ui.label("Migrating from PROCESS? Start with the guide below.").classes(
                    "text-caption text-grey q-mt-xs"
                )

        ui.separator().classes("q-my-sm")

        options = champion_template_options()
        labels = {o["case_id"]: o["label"] for o in options}
        stories = {o["case_id"]: o["story"] for o in options}
        with ui.row().classes("w-full items-end gap-4"):
            sel = ui.select(
                labels,
                label="Champion template (one-click starting point)",
                value=options[0]["case_id"] if options else None,
            ).classes("col-grow")
            story = ui.label(stories.get(options[0]["case_id"], "") if options else "").classes(
                "text-caption text-grey col-12"
            )

            def _on_sel() -> None:
                story.set_text(stories.get(str(sel.value), ""))

            sel.on("update:model-value", lambda: _on_sel())

            def _load() -> None:
                if not sel.value:
                    ui.notify("Select a champion template first.", type="warning")
                    return
                overrides = apply_champion_template(session, str(sel.value))
                ui.notify(
                    f"Loaded template: {labels.get(str(sel.value), sel.value)} "
                    f"({len(overrides)} inputs set). Click Evaluate Point.",
                    type="positive",
                )
                if on_loaded:
                    on_loaded()

            ui.button("Load template", icon="rocket_launch", on_click=_load).props("color=primary")

        with ui.row().classes("w-full gap-2 q-mt-sm"):
            for label, rel_path in STUDIO_DOC_LINKS:
                ui.button(
                    label,
                    icon="menu_book",
                    on_click=lambda p=rel_path: _open_doc_in_docs_library(session, p),
                ).props("flat dense color=primary")


def _dismiss(session: DesignSession) -> None:
    session.studio_entry_dismissed = True
    from ui_nicegui.lib.navigation import refresh_active_deck

    refresh_active_deck()
