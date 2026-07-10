"""Governance tab — contracts, reviewer pack, licensing pack (sub-tabs)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.publication_benchmarks import contract_studio, licensing_pack, regulatory_pack
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact
from ui_nicegui.session import DesignSession


def render_governance_panel(session: DesignSession) -> None:
    art = pick_session_run_artifact(session)
    if not isinstance(art, dict):
        from ui_nicegui.components.empty_state import empty_state

        empty_state(
            "No session run artifact — evaluate in **Point Designer** or **Systems Mode** first, "
            "then return for reviewer / licensing packs.",
            kind="warn",
        )
        with ui.row().classes("gap-2 q-mt-sm"):
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: switch_deck("Point Designer"),
            ).props("outline color=primary")
            ui.button(
                "Open Systems Mode",
                icon="hub",
                on_click=lambda: switch_deck("Systems Mode"),
            ).props("flat outline")
        ui.separator().classes("q-my-md")
        ui.label("Contract Studio still available without a run artifact.").classes("text-caption text-grey")

    with ui.tabs().classes("w-full") as tabs:
        t_contracts = ui.tab("Contracts")
        t_reviewer = ui.tab("Reviewer pack")
        t_licensing = ui.tab("Licensing")
    with ui.tab_panels(tabs, value=t_contracts).classes("w-full"):
        with ui.tab_panel(t_contracts):
            ui.label("Contract Studio").classes("text-subtitle1")
            contract_studio.render_contract_studio_panel(session)
        with ui.tab_panel(t_reviewer):
            regulatory_pack.render_regulatory_reviewer_pack(session)
        with ui.tab_panel(t_licensing):
            licensing_pack.render_licensing_tier2_pack(session)
