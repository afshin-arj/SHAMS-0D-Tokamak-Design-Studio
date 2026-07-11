"""Control Room — Orientation section."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.control_room_helpers import (
    LAUNCHPAD_DECK,
    LAUNCHPAD_PATHS,
    ORIENT_TABS,
    REFERENCE_GALLERY,
    read_doc,
)
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession


def render_orientation(session: DesignSession) -> None:
    if session.cr_orient_tab not in ORIENT_TABS:
        session.cr_orient_tab = ORIENT_TABS[0]

    ui.toggle(
        ORIENT_TABS,
        value=session.cr_orient_tab,
        on_change=lambda e: (
            setattr(session, "cr_orient_tab", str(e.value)),
            _panel.refresh(),
        ),
    ).classes("q-mb-md")

    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    tab = session.cr_orient_tab
    if tab == "Launchpad":
        ui.label("Launchpad — First 30 Minutes").classes("text-subtitle2")
        ui.label(
            "Guided entry path for fusion experts: choose intent, then open the recommended deck."
        ).classes("text-caption q-mb-sm")
        ui.select(
            [p[0] for p in LAUNCHPAD_PATHS],
            label="I want to…",
            value=session.cr_launchpad_path,
            on_change=lambda e: (
                setattr(session, "cr_launchpad_path", str(e.value)),
                _panel.refresh(),
            ),
        ).classes("w-full q-mb-sm")
        for title, info, body in LAUNCHPAD_PATHS:
            if title == session.cr_launchpad_path:
                ui.label(info).classes("text-body2 q-mb-xs")
                ui.markdown(body)
                deck = LAUNCHPAD_DECK.get(title)
                if deck:

                    def _open(d: str = deck) -> None:
                        switch_deck(d)
                        ui.notify(f"Opened {d}", type="info")

                    ui.button(f"Open {deck}", icon="open_in_new", on_click=_open).props("color=primary outline")
                break
    elif tab == "Vocabulary":
        ui.label("Vocabulary Ledger").classes("text-subtitle2")
        ui.label("Fusion-native terminology mapping (SHAMS ↔ common literature).").classes("text-caption q-mb-sm")
        with ui.scroll_area().classes("w-full").style("max-height: 480px"):
            ui.markdown(read_doc("docs/VOCABULARY_LEDGER.md", max_chars=12000))
    elif tab == "Reference Gallery":
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
    else:
        ui.label("Model Scope Card").classes("text-subtitle2")
        ui.label("Always-visible scope declaration for review rooms.").classes("text-caption q-mb-sm")
        with ui.scroll_area().classes("w-full").style("max-height: 480px"):
            ui.markdown(read_doc("docs/MODEL_SCOPE_CARD.md", max_chars=12000))
