"""Publication Benchmarks deck — 5-tab workflow (NiceGUI complete)."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.mode_scope import render_mode_scope
from ui_nicegui.components.verdict_banner import verdict_banner
from ui_nicegui.decks.publication_benchmarks import (
    atlas,
    benchmark_pack,
    crosscode,
    evidence_v387,
    governance,
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
from ui_nicegui.lib.pub_helpers import (
    pack_summary_from_outdir,
    render_pub_handoffs,
    render_pub_suite_handoff_shortcut,
)
from ui_nicegui.session import DesignSession


def _refresh_verdict() -> None:
    _render_deck_verdict.refresh()
    _render_deck_status.refresh()


@ui.refreshable
def _render_deck_status(session: DesignSession) -> None:
    step = normalize_pub_tab(session.pub_workflow_step)
    busy = bool(
        session.pub_running
        or session.pub_atlas_running
        or session.pub_atlas_fragility_running
        or session.pub_bench_running
    )
    if busy:
        ui.label("Running…").classes("text-caption text-orange")
        return
    if step == "1 · Constitutional Atlas":
        has_atlas = isinstance(session.pub_atlas_last, dict)
        ui.label("Atlas evaluated" if has_atlas else "Select a preset on tab 1 to begin").classes(
            "text-caption " + ("text-positive" if has_atlas else "text-grey")
        )
    elif step == "2 · Publication Pack":
        out = session.pub_bench_last_outdir
        ui.label(f"Pack ready: {out}" if out else "Acknowledge → generate publication pack").classes(
            "text-caption " + ("text-positive" if out else "text-grey")
        )
    elif step == "3 · Cross-Code Parity":
        ok = isinstance(session.pub_crosscode_last, dict)
        ui.label("Semantics compare ready" if ok else "Compare external clause semantics").classes(
            "text-caption " + ("text-positive" if ok else "text-grey")
        )
    elif step == "4 · Governance & Contracts":
        from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact_meta

        meta = pick_session_run_artifact_meta(session)
        if meta.get("loaded"):
            ui.label(f"Artifact: {meta.get('source')} · {meta.get('verdict', '-')}").classes(
                "text-caption text-positive"
            )
        else:
            ui.label("Need Point Designer / Systems / Atlas artifact").classes("text-caption text-grey")
    else:
        ready = isinstance(session.pub_v387_last_bytes, (bytes, bytearray)) and session.pub_v387_last_bytes
        ui.label("Evidence ZIP ready" if ready else "Build session evidence ZIP").classes(
            "text-caption " + ("text-positive" if ready else "text-grey")
        )


def render_publication_benchmarks(session: DesignSession) -> None:
    apply_deck_dsg_context(session, "bench")
    ui.label("Publication Benchmarks").classes("text-h5")
    ui.label(DECK_SUBTITLE).classes("text-caption text-grey q-mb-sm")
    render_mode_scope("bench", default_open=False)

    with ui.row().classes("w-full items-center justify-between q-mb-sm"):
        _render_deck_status(session)
        _render_mode_switches(session)

    _render_deck_verdict(session)
    _render_decision_chrome(session)

    session.pub_workflow_step = normalize_pub_tab(session.pub_workflow_step or session.pub_bench_tab)
    session.pub_bench_tab = session.pub_workflow_step
    ui.toggle(
        PUB_WORKFLOW_TABS,
        value=session.pub_workflow_step,
        on_change=lambda e: (
            setattr(session, "pub_workflow_step", normalize_pub_tab(str(e.value))),
            setattr(session, "pub_bench_tab", normalize_pub_tab(str(e.value))),
            _render_deck_verdict.refresh(),
            _render_deck_status.refresh(),
            _render_tab_body.refresh(),
        ),
    ).classes("w-full")
    help_text = TAB_HELP.get(normalize_pub_tab(session.pub_workflow_step), "")
    if help_text:
        ui.label(help_text).classes("text-caption text-grey q-mb-sm")

    # Suite shortcut always visible (D9-005); full handoff set stays in expansion (B5).
    on_crosscode = normalize_pub_tab(session.pub_workflow_step) == "3 · Cross-Code Parity"
    with ui.row().classes("w-full items-center gap-2 q-mb-sm flex-wrap"):
        with ui.expansion(
            "Cross-deck handoffs",
            icon="share",
            value=on_crosscode,
        ).classes("flex-1"):
            render_pub_handoffs(session)
        render_pub_suite_handoff_shortcut(session)

    _render_tab_body(session)


@ui.refreshable
def _render_mode_switches(session: DesignSession) -> None:
    """Guided and Expert are mutually exclusive — refresh widgets when either flips."""

    def _on_guided(e) -> None:
        session.pub_teaching_mode = bool(e.value)
        if session.pub_teaching_mode:
            session.pub_expert_view = False
        _render_mode_switches.refresh()
        _render_decision_chrome.refresh()
        _render_tab_body.refresh()
        _render_deck_status.refresh()

    def _on_expert(e) -> None:
        session.pub_expert_view = bool(e.value)
        if session.pub_expert_view:
            session.pub_teaching_mode = False
        _render_mode_switches.refresh()
        _render_decision_chrome.refresh()
        _render_tab_body.refresh()
        _render_deck_status.refresh()

    with ui.row().classes("gap-4"):
        ui.switch("Guided mode", value=bool(session.pub_teaching_mode), on_change=_on_guided)
        ui.switch("Expert view", value=bool(session.pub_expert_view), on_change=_on_expert)


@ui.refreshable
def _render_decision_chrome(session: DesignSession) -> None:
    def _on_decision(e) -> None:
        state = str(e.value)
        session.pub_decision_state = state
        tab = DECISION_TO_TAB.get(state)
        if tab and session.pub_teaching_mode:
            session.pub_workflow_step = tab
            session.pub_bench_tab = tab
            _render_tab_body.refresh()
            _render_deck_verdict.refresh()
            _render_deck_status.refresh()

    if session.pub_teaching_mode or not session.pub_expert_view:
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


@ui.refreshable
def _render_deck_verdict(session: DesignSession) -> None:
    step = normalize_pub_tab(session.pub_workflow_step)
    if step == "1 · Constitutional Atlas":
        summary = summarize_atlas_result(session.pub_atlas_last) if isinstance(session.pub_atlas_last, dict) else None
        if not isinstance(summary, dict) or not summary.get("loaded"):
            verdict_banner("UNKNOWN", detail="Select a tokamak preset and evaluate under Research or Reactor intent.")
            return
        posture = str(summary.get("verdict") or "UNKNOWN")
        diag_names = summary.get("failed_diagnostic") or summary.get("diagnostic_failures") or []
        if posture == "PASS":
            posture = "FEASIBLE"
        elif posture == "FAIL":
            posture = "INFEASIBLE"
        elif posture == "PASS+DIAG":
            posture = "FEASIBLE+DIAG"
        detail = (
            f"{summary.get('preset_label')} · {summary.get('dominant_mechanism', '-')} / "
            f"{summary.get('dominant_constraint', '-')} · "
            f"worst hard margin={summary.get('worst_hard_margin', '-')}"
        )
        if posture == "FEASIBLE+DIAG" and diag_names:
            detail += f" · diagnostics: {', '.join(str(x) for x in diag_names[:6])}"
        verdict_banner(posture, detail=detail)
        from ui_nicegui.decks.publication_benchmarks.verdict import render_atlas_verdict

        render_atlas_verdict(summary)
        ui.label(
            "Constitution clause maps are documentation semantics; blocking classification uses intent hard-set policy."
        ).classes("text-caption text-grey")
    elif step == "2 · Publication Pack":
        from ui_nicegui.lib.pub_helpers import render_pack_verdict_strip

        render_pack_verdict_strip(session)
    elif step == "3 · Cross-Code Parity":
        if isinstance(session.pub_crosscode_last, dict):
            comp = session.pub_crosscode_last
            verdict_banner(
                "SEMANTICS",
                detail=(
                    f"{comp.get('unknown_clause_count', '-')} unknown clauses · "
                    f"{len(comp.get('diff') or [])} diffs — documentation-level, not numeric PROCESS parity."
                ),
            )
        else:
            verdict_banner(
                "UNKNOWN",
                detail="Compare external clause semantics, or open System Suite for numeric PROCESS parity.",
            )
    elif step == "4 · Governance & Contracts":
        from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact

        art = pick_session_run_artifact(session)
        from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact_meta

        meta = pick_session_run_artifact_meta(session)
        if art:
            verdict_banner(
                "READY",
                detail=(
                    f"Source: {meta.get('source', 'session')} · verdict={meta.get('verdict', '-')} · "
                    "contracts / reviewer / licensing packs."
                ),
            )
        else:
            verdict_banner(
                "MISSING ARTIFACT",
                detail="Evaluate in Point Designer, Systems Mode, or Constitutional Atlas first.",
            )
    elif step == "5 · Evidence Export":
        if isinstance(session.pub_v387_last_bytes, (bytes, bytearray)) and session.pub_v387_last_bytes:
            verdict_banner("READY", detail="Session evidence ZIP built — download below.")
        else:
            verdict_banner("UNKNOWN", detail="Select cached sources and build a hash-locked evidence ZIP.")


@ui.refreshable
def _render_tab_body(session: DesignSession) -> None:
    step = normalize_pub_tab(session.pub_workflow_step)
    if step == "1 · Constitutional Atlas":
        atlas.render_constitutional_atlas(session, on_complete=_refresh_verdict)
    elif step == "2 · Publication Pack":
        benchmark_pack.render_benchmark_pack(session, on_complete=_refresh_verdict)
    elif step == "3 · Cross-Code Parity":
        crosscode.render_crosscode_constitutions(session, on_complete=_refresh_verdict)
    elif step == "4 · Governance & Contracts":
        governance.render_governance_panel(session)
    elif step == "5 · Evidence Export":
        evidence_v387.render_evidence_pack_v387(session, on_complete=_refresh_verdict)
