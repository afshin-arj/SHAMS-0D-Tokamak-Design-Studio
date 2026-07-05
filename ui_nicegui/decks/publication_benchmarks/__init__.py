"""Publication Benchmarks deck — 5-tab workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.decks.publication_benchmarks import (
    atlas,
    benchmark_pack,
    crosscode,
    evidence_v387,
    governance,
    verdict,
)
from ui_nicegui.lib.benchmark_helpers import summarize_atlas_result
from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context
from ui_nicegui.lib.pub_benchmark_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    DECK_SUBTITLE,
    PUB_WORKFLOW_TABS,
    TAB_HELP,
    normalize_pub_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def _refresh_verdict() -> None:
    _render_deck_verdict.refresh()


def render_publication_benchmarks(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "bench")
    ui.label("Publication Benchmarks").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("bench", default_open=False)

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        has_atlas = isinstance(session.pub_atlas_last, dict)
        ui.label(
            "Atlas evaluated" if has_atlas else "Select a preset on tab 1 to begin"
        ).classes("text-caption " + ("text-positive" if has_atlas else "text-grey"))
        with ui.row().classes("gap-4"):
            ui.switch(
                "Guided mode",
                value=session.pub_teaching_mode,
                on_change=lambda e: (
                    setattr(session, "pub_teaching_mode", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )
            ui.switch(
                "Expert view",
                value=session.pub_expert_view,
                on_change=lambda e: (
                    setattr(session, "pub_expert_view", bool(e.value)),
                    _render_tab_body.refresh(),
                ),
            )

    _render_deck_verdict(session)

    def _on_decision(e) -> None:
        state = str(e.value)
        session.pub_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.pub_teaching_mode:
            session.pub_workflow_step = tab
            session.pub_bench_tab = tab
            _render_tab_body.refresh()

    ui.select(
        DECISION_STATES,
        label="What are you trying to do?",
        value=session.pub_decision_state
        if session.pub_decision_state in DECISION_STATES
        else DECISION_STATES[0],
        on_change=_on_decision,
    ).classes("w-full q-mb-xs")

    banner = teaching_banner(session)
    if banner:
        ui.markdown(banner).classes("text-caption q-mb-sm")

    session.pub_workflow_step = normalize_pub_tab(session.pub_workflow_step or session.pub_bench_tab)
    session.pub_bench_tab = session.pub_workflow_step
    ui.toggle(
        PUB_WORKFLOW_TABS,
        value=session.pub_workflow_step,
        on_change=lambda e: (
            setattr(session, "pub_workflow_step", normalize_pub_tab(str(e.value))),
            setattr(session, "pub_bench_tab", normalize_pub_tab(str(e.value))),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_pub_tab(session.pub_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    _render_tab_body(session)


@ui.refreshable
def _render_deck_verdict(session: DesignSession) -> None:
    step = normalize_pub_tab(session.pub_workflow_step)
    if step == "1 · Constitutional Atlas":
        summary = summarize_atlas_result(session.pub_atlas_last) if isinstance(session.pub_atlas_last, dict) else None
        verdict.render_atlas_verdict(summary)
    elif step == "2 · Publication Pack" and session.pub_bench_last_outdir:
        ui.label("Last pack").classes("text-subtitle2")
        ui.label(f"{session.pub_bench_last_outdir} (rc={session.pub_bench_last_rc})").classes("text-caption")
    elif step == "3 · Cross-Code Parity" and isinstance(session.pub_crosscode_last, dict):
        comp = session.pub_crosscode_last
        ui.label(
            f"Cross-code diff: {comp.get('unknown_clause_count', '-')} unknown · "
            f"{len(comp.get('diff') or [])} diff entries"
        ).classes("text-caption")


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_pub_tab(session.pub_workflow_step)
    if step == "1 · Constitutional Atlas":
        atlas.render_constitutional_atlas(session, on_complete=_refresh_verdict)
    elif step == "2 · Publication Pack":
        benchmark_pack.render_benchmark_pack(session)
    elif step == "3 · Cross-Code Parity":
        crosscode.render_crosscode_constitutions(session)
    elif step == "4 · Governance & Contracts":
        governance.render_governance_panel(session)
    elif step == "5 · Evidence Export":
        evidence_v387.render_evidence_pack_v387(session)
