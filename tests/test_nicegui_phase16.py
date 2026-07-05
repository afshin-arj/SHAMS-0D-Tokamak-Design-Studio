"""Phase 16: Publication Benchmarks remainder + launch helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui_nicegui.app import _pick_port
from ui_nicegui.decks.publication_benchmarks import (
    benchmark_pack,
    contract_studio,
    crosscode,
    evidence_v387,
    render_publication_benchmarks,
)
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    build_evidence_pack_v387,
    compare_crosscode,
    contract_bundle_zip,
    list_crosscode_items,
    session_cache_sources,
    validate_contracts,
)
from ui_nicegui.session import DesignSession


def test_phase16_renderers_import() -> None:
    assert callable(render_publication_benchmarks)
    assert callable(crosscode.render_crosscode_constitutions)
    assert callable(benchmark_pack.render_benchmark_pack)
    assert callable(contract_studio.render_contract_studio_panel)
    assert callable(evidence_v387.render_evidence_pack_v387)


def test_pick_port_smoke() -> None:
    port = _pick_port("127.0.0.1", 18080, span=5)
    assert 18080 <= port < 18085


def test_list_crosscode_items_smoke() -> None:
    items = list_crosscode_items()
    if not items:
        pytest.skip("No cross-code constitution data files")
    assert items[0][1].exists()


def test_compare_crosscode_smoke() -> None:
    items = list_crosscode_items()
    if not items:
        pytest.skip("No cross-code constitution data files")
    comp = compare_crosscode(items[0][1], "research")
    assert comp.get("schema") == "crosscode_comparison.v1"
    assert "diff" in comp


def test_validate_contracts_smoke() -> None:
    recs, summary = validate_contracts()
    assert isinstance(recs, list)
    assert isinstance(summary, dict)
    assert summary.get("n_contracts", 0) >= 1


def test_contract_bundle_zip_smoke() -> None:
    data = contract_bundle_zip()
    assert len(data) > 100
    assert data[:2] == b"PK"


def test_evidence_pack_v387_smoke(tmp_path: Path) -> None:
    s = DesignSession()
    s.pd_last_artifact = {"outputs": {"Q": 1.0}, "kind": "shams_run_artifact"}
    cache = session_cache_sources(s)
    out = tmp_path / "evidence_pack_v387.zip"
    res = build_evidence_pack_v387(
        out,
        shams_version="test",
        sources=cache,
        include={"pd_last_outputs": True},
        notes="unit test",
    )
    assert res.zip_path.exists()
    assert res.index.get("n_sources") == 1
    assert len(res.zip_bytes) > 100
