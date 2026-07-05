"""Control Room deck — NiceGUI Batch 10 + Phase 15 Provenance."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.control_room import artifacts, chronicle, constitution, diagnostics, orientation, provenance, verdict
from ui_nicegui.lib.control_room_helpers import CR_SECTIONS, governance_summary
from ui_nicegui.session import DesignSession

_PORTED = {"Orientation", "Constitution", "Diagnostics", "Provenance", "Artifacts", "Chronicle"}


def render_control_room(session: DesignSession) -> None:
    ui.label("Control Room").classes("text-h5")
    ui.label(
        "Governance, provenance, exports, and expert diagnostics — organized as compact decks."
    ).classes("text-caption text-grey q-mb-sm")

    summary = governance_summary(session)
    verdict.render_governance_verdict(summary)

    ui.select(
        CR_SECTIONS,
        label="Section",
        value=session.cr_section,
        on_change=lambda e: setattr(session, "cr_section", str(e.value)),
    ).classes("w-full q-my-md")

    if session.cr_section == "Orientation":
        orientation.render_orientation(session)
    elif session.cr_section == "Constitution":
        constitution.render_constitution(session)
    elif session.cr_section == "Diagnostics":
        diagnostics.render_diagnostics(session)
    elif session.cr_section == "Provenance":
        provenance.render_provenance(session)
    elif session.cr_section == "Artifacts":
        artifacts.render_artifacts(session)
    elif session.cr_section == "Chronicle":
        chronicle.render_chronicle(session)
    elif session.cr_section not in _PORTED:
        empty_state(
            f"**{session.cr_section}** is not yet ported to NiceGUI "
            "(artifact explorer, chronicle instruments, constraint cockpit, and other expert panels). "
            "Use Streamlit: `run_ui.cmd`.",
            kind="info",
        )
