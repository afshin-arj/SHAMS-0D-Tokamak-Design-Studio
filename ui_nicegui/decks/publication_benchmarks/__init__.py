"""Publication Benchmarks deck — NiceGUI Batch 9 + Phase 16 remainder."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.decks.publication_benchmarks import (
    atlas,
    benchmark_pack,
    contract_studio,
    crosscode,
    evidence_v387,
)
from ui_nicegui.lib.benchmark_helpers import PUB_BENCH_TABS
from ui_nicegui.session import DesignSession

ATLAS_TAB = "Tokamak Constitutional Atlas"
CROSSCODE_TAB = "Cross-Code Constitutions"
BENCHMARK_TAB = "Publication Benchmarks"
CONTRACT_TAB = "Contract Studio"
EVIDENCE_TAB = "Regulatory Evidence Pack Builder (v387)"


def render_publication_benchmarks(session: DesignSession) -> None:
    ui.label("Publication Benchmarks").classes("text-h5")
    ui.label(
        "Benchmark suite: publication tables and the Tokamak Constitutional Atlas "
        "(preset-driven, intent-aware)."
    ).classes("text-caption text-grey q-mb-sm")

    if session.pub_bench_tab not in PUB_BENCH_TABS:
        session.pub_bench_tab = ATLAS_TAB

    ui.select(
        PUB_BENCH_TABS,
        label="Section",
        value=session.pub_bench_tab,
        on_change=lambda e: setattr(session, "pub_bench_tab", str(e.value)),
    ).classes("w-full q-mb-md")

    tab = session.pub_bench_tab
    if tab == ATLAS_TAB:
        ui.label("Tokamak Constitutional Atlas").classes("text-subtitle1")
        ui.label(
            "Select a famous tokamak preset and evaluate under Research or Reactor intent. "
            "No tuning. Deterministic, reviewer-safe."
        ).classes("text-caption q-mb-sm")
        atlas.render_constitutional_atlas(session)
    elif tab == CROSSCODE_TAB:
        crosscode.render_crosscode_constitutions(session)
    elif tab == BENCHMARK_TAB:
        benchmark_pack.render_benchmark_pack(session)
    elif tab == CONTRACT_TAB:
        contract_studio.render_contract_studio_panel(session)
    elif tab == EVIDENCE_TAB:
        evidence_v387.render_evidence_pack_v387(session)
