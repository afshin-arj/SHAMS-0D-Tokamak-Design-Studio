"""Publication Benchmarks workflow tests."""
from __future__ import annotations

from ui_nicegui.decks.publication_benchmarks import render_publication_benchmarks
from ui_nicegui.lib.benchmark_helpers import (
    atlas_evidence_json,
    atlas_result_to_dict,
    build_preset_buckets,
    evaluate_atlas,
    summarize_atlas_result,
)
from ui_nicegui.lib.pub_benchmark_extended_helpers import pick_session_run_artifact
from ui_nicegui.lib.pub_benchmark_labels import (
    DECISION_TO_TAB,
    PUB_WORKFLOW_TABS,
    normalize_pub_tab,
)
from ui_nicegui.session import DesignSession


def test_atlas_preset_controls_use_stable_keys() -> None:
    """D9-002: Tokamak select binds preset keys (dict options), not display labels alone."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath(
        "ui_nicegui", "decks", "publication_benchmarks", "atlas.py"
    ).read_text(encoding="utf-8")
    assert "key_to_label" in src
    assert "data-testid=pb-atlas-category" in src
    assert "data-testid=pb-atlas-tokamak" in src
    assert "use-input" in src
    assert "def _preset_controls" in src
    buckets = build_preset_buckets()
    assert "Large-Scale & Program" in buckets or "Compact / HTS" in buckets
    all_keys = [o[0] for opts in buckets.values() for o in opts]
    assert any("ITER" in k for k in all_keys)
    assert any("SPARC" in k for k in all_keys)


def test_pub_workflow_tabs() -> None:
    assert len(PUB_WORKFLOW_TABS) == 5
    assert normalize_pub_tab("Tokamak Constitutional Atlas") == "1 · Constitutional Atlas"
    assert DECISION_TO_TAB["Generate publication tables for machines"] == "2 · Publication Pack"


def test_atlas_evaluate_and_summary() -> None:
    buckets = build_preset_buckets()
    key = buckets[next(iter(buckets.keys()))][0][0]
    d = atlas_result_to_dict(evaluate_atlas(key, "Research"))
    summary = summarize_atlas_result(d)
    assert summary["loaded"] is True
    assert summary["verdict"] in ("PASS", "FAIL", "PASS+DIAG", "-", "FEASIBLE", "INFEASIBLE")
    assert "design_confidence" in summary
    data = atlas_evidence_json(d)
    assert b"preset_key" in data


def test_pick_session_artifact_empty() -> None:
    s = DesignSession()
    assert pick_session_run_artifact(s) is None
