"""Control Room — Constitution section."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.control_room_helpers import CONST_TABS, list_docs, read_capability_matrix, read_doc
from ui_nicegui.session import DesignSession


def render_constitution(session: DesignSession) -> None:
    with ui.tabs().classes("w-full") as tabs:
        tab_widgets = {name: ui.tab(name) for name in CONST_TABS}

    with ui.tab_panels(tabs, value=tab_widgets[session.cr_const_tab]).classes("w-full"):
        with ui.tab_panel(tab_widgets["Model Ledger"]):
            ui.label("0-D Tokamak Physics Model (Phase-1)").classes("text-subtitle2")
            ui.label("Frozen truth boundary — read-only model structure and assumptions.").classes("text-caption q-mb-sm")
            with ui.scroll_area().classes("w-full").style("max-height: 520px"):
                ui.markdown(read_doc("docs/PHYSICAL_MODELS_0D.md", max_chars=14000))

        with ui.tab_panel(tab_widgets["Capability Matrix"]):
            ui.label("Physics Capability Matrix").classes("text-subtitle2")
            ui.label(
                "Read-only audit map: subsystems → equations/closures → authority tier → validity domain."
            ).classes("text-caption q-mb-sm")
            with ui.scroll_area().classes("w-full").style("max-height: 520px"):
                ui.markdown(read_capability_matrix())

        with ui.tab_panel(tab_widgets["Docs Library"]):
            ui.label("Documentation library").classes("text-subtitle2")
            docs = list_docs()
            if not docs:
                ui.label("No docs/ folder found in this build.").classes("text-grey")
                return
            if not session.cr_docs_sel or session.cr_docs_sel not in docs:
                session.cr_docs_sel = docs[0]
            ui.select(
                docs,
                label="Open a doc (read-only)",
                value=session.cr_docs_sel,
                on_change=lambda e: setattr(session, "cr_docs_sel", str(e.value)),
            ).classes("w-full q-mb-sm")
            with ui.scroll_area().classes("w-full").style("max-height: 480px"):
                ui.markdown(read_doc(f"docs/{session.cr_docs_sel}", max_chars=16000))
