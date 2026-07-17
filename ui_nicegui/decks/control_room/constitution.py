"""Control Room — Constitution section."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.control_room import assumptions_panel, constraint_provenance, constraints_governance
from ui_nicegui.lib.control_room_helpers import (
    CONST_TABS,
    MIGRATION_GUIDE_DOC,
    list_docs,
    read_capability_matrix,
    read_doc,
)
from ui_nicegui.session import DesignSession


def render_constitution(session: DesignSession) -> None:
    if session.cr_const_tab not in CONST_TABS:
        session.cr_const_tab = CONST_TABS[0]

    ui.toggle(
        CONST_TABS,
        value=session.cr_const_tab,
        on_change=lambda e: (
            setattr(session, "cr_const_tab", str(e.value)),
            _panel.refresh(),
        ),
    ).classes("q-mb-md")

    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    tab = session.cr_const_tab
    if tab == "Model Ledger":
        ui.label("0-D Tokamak Physics Model (Phase-1)").classes("text-subtitle2")
        ui.label("Frozen truth boundary — read-only model structure and assumptions.").classes("text-caption q-mb-sm")
        with ui.scroll_area().classes("w-full").style("max-height: 520px"):
            ui.markdown(read_doc("docs/PHYSICAL_MODELS_0D.md", max_chars=14000))
    elif tab == "Capability Matrix":
        ui.label("Physics Capability Matrix").classes("text-subtitle2")
        ui.label(
            "Read-only audit map: subsystems → equations/closures → authority tier → validity domain."
        ).classes("text-caption q-mb-sm")
        with ui.scroll_area().classes("w-full").style("max-height: 520px"):
            ui.markdown(read_capability_matrix())
    elif tab == "Assumptions":
        assumptions_panel.render_assumptions_panel(session)
    elif tab == "Constraints":
        constraints_governance.render_constraints_governance(session)
    elif tab == "Constraint Provenance":
        constraint_provenance.render_constraint_provenance(session)
    else:
        ui.label("Documentation library").classes("text-subtitle2")
        ui.label(
            "PROCESS handoff: open PROCESS_TO_SHAMS_MIGRATION_GUIDE.md for IN.DAT→PointInputs, "
            "MFILE→artifacts, CCFS propose-only, and citation rules (no invented MFILE numbers)."
        ).classes("text-caption q-mb-sm")
        docs = list_docs()
        if not docs:
            ui.label("No docs/ folder found in this build.").classes("text-grey")
            return
        if not session.cr_docs_sel or session.cr_docs_sel not in docs:
            session.cr_docs_sel = MIGRATION_GUIDE_DOC if MIGRATION_GUIDE_DOC in docs else docs[0]
        ui.select(
            docs,
            label="Open a doc (read-only)",
            value=session.cr_docs_sel,
            on_change=lambda e: setattr(session, "cr_docs_sel", str(e.value)),
        ).classes("w-full q-mb-sm")
        with ui.scroll_area().classes("w-full").style("max-height: 480px"):
            ui.markdown(read_doc(f"docs/{session.cr_docs_sel}", max_chars=16000))
