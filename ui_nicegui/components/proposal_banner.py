"""Proposal-only firewall banner for external optimizer decks."""
from __future__ import annotations

from nicegui import ui

PROPOSAL_DISCLAIMER = (
    "**Proposal-only firewall** — external optimizers and surrogate layers propose inputs only. "
    "SHAMS re-evaluates with frozen truth; infeasibility is reported, not negotiated."
)


def render_proposal_banner(*, title: str = "External optimizer panel") -> None:
    with ui.card().classes("w-full bg-amber-1 q-mb-md"):
        ui.label(title).classes("text-subtitle2")
        ui.markdown(PROPOSAL_DISCLAIMER).classes("text-caption")
