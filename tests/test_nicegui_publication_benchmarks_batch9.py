"""Batch 9: Publication Benchmarks / Constitutional Atlas wiring."""
from __future__ import annotations

from ui_nicegui.decks.publication_benchmarks import render_publication_benchmarks
from ui_nicegui.lib.benchmark_helpers import (
    atlas_evidence_json,
    atlas_result_to_dict,
    build_preset_buckets,
    constitution_diff_rows,
    evaluate_atlas,
    run_fragility_scan,
    summarize_atlas_result,
)


def test_publication_benchmarks_renderer_import() -> None:
    assert callable(render_publication_benchmarks)


def test_build_preset_buckets() -> None:
    buckets = build_preset_buckets()
    assert isinstance(buckets, dict)
    assert len(buckets) >= 1
    first = next(iter(buckets.values()))
    assert len(first) >= 1


def test_evaluate_atlas_smoke() -> None:
    buckets = build_preset_buckets()
    key = buckets[next(iter(buckets.keys()))][0][0]
    res = evaluate_atlas(key, "Research")
    d = atlas_result_to_dict(res)
    summary = summarize_atlas_result(d)
    assert summary["loaded"] is True
    assert summary["verdict"] in ("PASS", "FAIL", "PASS+DIAG", "-")


def test_fragility_scan_smoke() -> None:
    buckets = build_preset_buckets()
    key = buckets[next(iter(buckets.keys()))][0][0]
    scan = run_fragility_scan(key, "Research")
    assert isinstance(scan, dict)
    assert "pass_fraction" in scan


def test_atlas_evidence_export() -> None:
    buckets = build_preset_buckets()
    key = buckets[next(iter(buckets.keys()))][0][0]
    d = atlas_result_to_dict(evaluate_atlas(key, "Reactor"))
    data = atlas_evidence_json(d)
    assert b"preset_key" in data
    rows = constitution_diff_rows(d)
    assert isinstance(rows, list)
