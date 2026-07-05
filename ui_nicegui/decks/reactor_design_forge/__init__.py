"""Reactor Design Forge deck — NiceGUI Batch 7 + Phase 14 Machine Finder & Capsules."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.decks.reactor_design_forge import (
    capsules,
    intent_compiler,
    machine_finder,
    verdict,
)
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.forge_helpers import FORGE_DECKS, summarize_forge_state
from ui_nicegui.lib.forge_machine_finder_helpers import summarize_workbench_run
from ui_nicegui.session import DesignSession


def _refresh() -> None:
    _render_dashboard.refresh()


def _set_forge_review_mode(session: DesignSession, value: bool) -> None:
    session.forge_review_mode = bool(value)
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()


def render_reactor_design_forge(session: DesignSession) -> None:
    ui.label("Reactor Design Forge").classes("text-h5")
    ui.label(
        "Concept assembly + candidate archives + traces. Feeds the frozen evaluator; does not replace it."
    ).classes("text-caption text-grey q-mb-sm")

    ui.markdown(
        "**Non-authoritative workspace** — produces candidate archives and traces. "
        "Truth remains in the frozen evaluator. Nothing is applied automatically."
    ).classes("text-body2 q-mb-sm")

    ui.switch(
        "Review Mode (locks exploration controls)",
        value=session.forge_review_mode,
        on_change=lambda e: _set_forge_review_mode(session, bool(e.value)),
    ).classes("q-mb-sm")

    if session.forge_review_mode:
        ui.label("Review Mode: exploration controls locked; inspect artifacts only.").classes("text-orange")

    ui.toggle(
        FORGE_DECKS,
        value=session.forge_deck,
        on_change=lambda e: setattr(session, "forge_deck", str(e.value)),
    ).classes("q-mb-md")

    _, _, point_out = get_point_artifact_triple(session)
    if not isinstance(point_out, dict):
        empty_state(
            "Run **Point Designer** first — Forge uses the last evaluated point as compilation baseline.",
            kind="info",
        )
        return

    _render_dashboard(session)

    if session.forge_deck == "Intent Compiler":
        if session.forge_review_mode:
            ui.label("Review Mode: compile disabled. Switch off Review Mode to compile new candidates.").classes(
                "text-caption text-grey"
            )
        else:
            ui.separator()
            intent_compiler.render_intent_compiler(session, on_complete=_refresh)
    elif session.forge_deck == "Machine Finder":
        ui.separator()
        machine_finder.render_machine_finder(
            session,
            review_mode=session.forge_review_mode,
            on_complete=_refresh,
        )
    else:
        ui.separator()
        capsules.render_capsules(session, on_complete=_refresh)


@ui.refreshable
def _render_dashboard(session: DesignSession) -> None:
    summary = summarize_forge_state(session.forge_intent_compiler_last, session.forge_last_audit)
    wb = summarize_workbench_run(session.forge_workbench_run)
    if wb.get("loaded") and session.forge_deck in ("Machine Finder", "Capsules"):
        summary = {
            **summary,
            "workbench_loaded": True,
            "audit_verdict": f"Archive {wb.get('n_feasible_archive')}/{wb.get('n_archive')} feasible",
            "dominant": wb.get("top_blocker") or wb.get("dominant_resistance") or summary.get("dominant"),
        }
    verdict.render_forge_dashboard(summary)
