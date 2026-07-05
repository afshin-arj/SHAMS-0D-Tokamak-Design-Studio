"""Control Room — Orientation section."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.control_room_helpers import (
    LAUNCHPAD_PATHS,
    ORIENT_TABS,
    REFERENCE_GALLERY,
    read_doc,
)
from ui_nicegui.session import DesignSession


def render_orientation(session: DesignSession) -> None:
    with ui.tabs().classes("w-full") as tabs:
        tab_widgets = {name: ui.tab(name) for name in ORIENT_TABS}

    with ui.tab_panels(tabs, value=tab_widgets[session.cr_orient_tab]).classes("w-full"):
        with ui.tab_panel(tab_widgets["Launchpad"]):
            ui.label("Launchpad — First 30 Minutes").classes("text-subtitle2")
            ui.label(
                "Guided entry path for fusion experts: choose intent, then follow a minimal, honest workflow."
            ).classes("text-caption q-mb-sm")
            ui.select(
                [p[0] for p in LAUNCHPAD_PATHS],
                label="I want to…",
                value=session.cr_launchpad_path,
                on_change=lambda e: setattr(session, "cr_launchpad_path", str(e.value)),
            ).classes("w-full q-mb-sm")
            for title, info, body in LAUNCHPAD_PATHS:
                if title == session.cr_launchpad_path:
                    ui.label(info).classes("text-body2 q-mb-xs")
                    ui.markdown(body)
                    break

        with ui.tab_panel(tab_widgets["Vocabulary"]):
            ui.label("Vocabulary Ledger").classes("text-subtitle2")
            ui.label("Fusion-native terminology mapping (SHAMS ↔ common literature).").classes("text-caption q-mb-sm")
            with ui.scroll_area().classes("w-full").style("max-height: 480px"):
                ui.markdown(read_doc("docs/VOCABULARY_LEDGER.md", max_chars=12000))

        with ui.tab_panel(tab_widgets["Reference Gallery"]):
            ui.label("Reference Study Gallery").classes("text-subtitle2")
            ui.label("Recognizable anchors for the community — reference contexts, not targets.").classes(
                "text-caption q-mb-sm"
            )
            for name, note in REFERENCE_GALLERY:
                with ui.expansion(name, icon="bookmark").classes("w-full"):
                    ui.label(note)
            ui.label("Tip: use these as discussion anchors when presenting SHAMS outputs to reviewers.").classes(
                "text-caption text-grey q-mt-sm"
            )

        with ui.tab_panel(tab_widgets["Scope"]):
            ui.label("Model Scope Card").classes("text-subtitle2")
            ui.label("Always-visible scope declaration for review rooms.").classes("text-caption q-mb-sm")
            with ui.scroll_area().classes("w-full").style("max-height: 480px"):
                ui.markdown(read_doc("docs/MODEL_SCOPE_CARD.md", max_chars=12000))
