"""Trade Study Studio deck — NiceGUI Batch 6.

Deterministic trade studies over knob sets; Pareto over feasible points only.
Advanced decks (atlas, mirage, external optimizers) deferred to Streamlit.
"""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.trade_study_studio import advanced, controls, results, verdict
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.trade_study_helpers import ADVANCED_DECKS, STUDY_SETUP_DECK
from ui_nicegui.session import DesignSession


def _refresh_after_run() -> None:
    _render_dashboard.refresh()
    _render_results.refresh()


def render_trade_study_studio(session: DesignSession) -> None:
    ui.label("Trade Study Studio").classes("text-h5")
    ui.label(
        "Feasibility-first trade studies + firewalled optimizer kits. "
        "Truth remains frozen; optimization is proposal-only."
    ).classes("text-caption text-grey q-mb-sm")

    with ui.expansion("Scope: what this mode does / does not do", icon="info").classes("w-full q-mb-sm"):
        ui.markdown(
            "**Does:** budgeted LHS trade studies, Pareto over feasible points, study capsules.\n\n"
            "**Does not:** modify frozen physics, use internal solvers, or claim a globally best machine."
        )

    ui.select(
        [STUDY_SETUP_DECK] + ADVANCED_DECKS,
        label="Studio deck",
        value=session.trade_studio_deck,
        on_change=lambda e: setattr(session, "trade_studio_deck", str(e.value)),
    ).classes("w-full q-mb-md")

    if session.trade_studio_deck != STUDY_SETUP_DECK:
        if session.trade_studio_deck in ADVANCED_DECKS:
            advanced.render_advanced_deck(session, session.trade_studio_deck)
        else:
            empty_state(
                f"**{session.trade_studio_deck}** is not yet ported to NiceGUI. "
                "Use Streamlit: `run_ui.cmd`.",
                kind="info",
            )
        return

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer** first — Trade Study uses the last evaluated point as baseline.",
            kind="info",
        )
        return

    _render_dashboard(session)
    ui.separator()
    controls.render_study_controls(session, on_complete=_refresh_after_run)
    _render_results(session)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = None
    if isinstance(session.trade_last, dict):
        summary = session.trade_last.get("summary")
    verdict.render_study_dashboard(summary)


@ui.refreshable
def _render_results(session: DesignSession) -> None:
    if not isinstance(session.trade_last, dict):
        return
    ui.separator()
    results.render_study_results(session, session.trade_last)
