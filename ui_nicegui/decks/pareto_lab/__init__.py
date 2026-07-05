"""Pareto Lab deck — NiceGUI Batch 5 (Internal Pareto Frontier).

LHS sampling over feasible set; constraint-annotated Pareto fronts.
External optimizer decks deferred to Streamlit.
"""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.pareto_lab import controls, external, results, verdict
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.session import DesignSession

PARETO_LOCK_LINE = (
    "**Pareto Lab is frozen** — Trade-off cartography over **feasible** designs only. "
    "No optimization, relaxation, or recommendations."
)

INTERNAL_DECK = "Internal Pareto Frontier"
EXTERNAL_DECKS = [
    "Robust Pareto Frontier (Phase+UQ)",
    "Regime-Conditioned Pareto Atlas 2.0",
    "Certified Optimization Orchestrator",
    "Feasible Optimizer (External)",
    "Concept Optimization Cockpit",
    "External Optimization Workbench",
    "External Optimization Interpretation",
    "Design Family Narratives",
    "External Optimizer Co-Pilot",
    "External Optimizer Suite",
    "Optimization Evidence Packs",
]


def _refresh_after_run() -> None:
    _render_dashboard.refresh()
    _render_results.refresh()


def render_pareto_lab(session: DesignSession) -> None:
    ui.label("Pareto Lab").classes("text-h5")
    ui.label(
        "Trade-off observatory over the feasible set. External optimization is firewalled; truth remains frozen."
    ).classes("text-caption text-grey q-mb-sm")

    ui.markdown(PARETO_LOCK_LINE).classes("text-body2 q-mb-sm")

    ui.select(
        [INTERNAL_DECK] + EXTERNAL_DECKS,
        label="Pareto Lab deck",
        value=session.pareto_deck,
        on_change=lambda e: setattr(session, "pareto_deck", str(e.value)),
    ).classes("w-full q-mb-md")

    if session.pareto_deck != INTERNAL_DECK:
        if session.pareto_deck in EXTERNAL_DECKS:
            external.render_external_deck(session, session.pareto_deck)
        else:
            empty_state(
                f"**{session.pareto_deck}** is not yet ported to NiceGUI. "
                "Use Streamlit: `run_ui.cmd`.",
                kind="info",
            )
        return

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer** first — Pareto Lab uses the last evaluated point as baseline.",
            kind="info",
        )
        return

    with ui.expansion("What does Pareto optimal mean here?", icon="help").classes("w-full q-mb-sm"):
        ui.markdown(
            "Non-dominated **feasible** points for declared objectives and intent. "
            "Descriptive trade-off slice — never a recommendation."
        )

    _render_dashboard(session)
    ui.separator()
    controls.render_pareto_controls(session, on_complete=_refresh_after_run)
    _render_results(session)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = None
    if isinstance(session.pareto_last, dict):
        summary = session.pareto_last.get("summary")
    verdict.render_frontier_dashboard(summary)


@ui.refreshable
def _render_results(session: DesignSession) -> None:
    if not isinstance(session.pareto_last, dict):
        return
    ui.separator()
    results.render_pareto_results(session, session.pareto_last)
