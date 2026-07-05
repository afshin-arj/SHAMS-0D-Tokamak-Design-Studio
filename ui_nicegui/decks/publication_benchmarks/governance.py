"""Governance tab — contracts, reviewer pack, licensing pack."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.publication_benchmarks import contract_studio, licensing_pack, regulatory_pack
from ui_nicegui.session import DesignSession


def render_governance_panel(session: DesignSession) -> None:
    ui.label("Contract Studio").classes("text-subtitle1")
    contract_studio.render_contract_studio_panel(session)
    ui.separator().classes("q-my-md")
    regulatory_pack.render_regulatory_reviewer_pack(session)
    ui.separator().classes("q-my-md")
    licensing_pack.render_licensing_tier2_pack(session)
