"""Independence ticket 1.3 — PROCESS parity corpus honesty + hashed dossiers."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.parity_harness.delta_dossier import (
    build_delta_dossier,
    classify_dossier_status,
    has_numeric_process_kpis,
)
from src.parity_harness.process_corpus import (
    DEFAULT_CORPUS_PATH,
    load_process_reference_corpus,
    sha256_hex,
    validate_corpus_honesty,
    verify_corpus_dossier_hashes,
)


def test_classify_method_only_when_no_numeric_process() -> None:
    assert classify_dossier_status(None) == "METHOD-ONLY"
    assert classify_dossier_status({}) == "METHOD-ONLY"
    assert classify_dossier_status({"Q_plasma": None, "P_fus_MW": None}) == "METHOD-ONLY"
    assert not has_numeric_process_kpis({"Q_plasma": None})


def test_classify_numeric_when_real_kpi_present() -> None:
    assert classify_dossier_status({"Q_plasma": 10.0}) == "NUMERIC"
    assert has_numeric_process_kpis({"kpis": {"Pe_net_MW": 100.0}})


def test_build_delta_dossier_method_only_label() -> None:
    art = {
        "verdict": "FEASIBLE",
        "kpis": {"Q_plasma": 5.0, "P_fus_MW": 100.0},
        "constraint_ledger": {"top_blockers": []},
    }
    d = build_delta_dossier(case_id="t1", shams_artifact=art, process_payload=None)
    assert d["dossier_status"] == "METHOD-ONLY"
    assert d["has_process_reference"] is False
    assert d["honesty"]["label"] == "METHOD-ONLY"
    assert d["kpi_deltas"] == []
    assert d["shams_kpis"]["Q_plasma"] == 5.0


def test_extract_shams_kpi_aliases_from_artifact() -> None:
    art = {
        "kpis": {
            "feasible_hard": False,
            "Q_DT_eqv": 1.7,
            "Pfus_DT_adj_MW": 80.0,
            "P_net_e_MW": 12.0,
            "min_hard_margin": -1.0,
        },
        "dominant_mechanism": "GENERAL",
        "dominant_constraint": "divertor",
        "constraint_ledger": {},
    }
    d = build_delta_dossier(case_id="alias", shams_artifact=art, process_payload=None)
    assert d["shams_kpis"]["Q_plasma"] == pytest.approx(1.7)
    assert d["shams_kpis"]["P_fus_MW"] == pytest.approx(80.0)
    assert d["shams_kpis"]["Pe_net_MW"] == pytest.approx(12.0)
    assert d["shams_summary"]["verdict"] == "NO-SOLUTION"
    assert d["shams_summary"]["dominant_mechanism"] == "GENERAL"


def test_build_delta_dossier_numeric_deltas() -> None:
    art = {"verdict": "FEASIBLE", "kpis": {"Q_plasma": 12.0}, "constraint_ledger": {}}
    d = build_delta_dossier(
        case_id="t2",
        shams_artifact=art,
        process_payload={"Q_plasma": 10.0},
    )
    assert d["dossier_status"] == "NUMERIC"
    assert d["has_process_reference"] is True
    rows = {r["field"]: r for r in d["kpi_deltas"]}
    assert rows["Q_plasma"]["delta"] == pytest.approx(2.0)


def test_corpus_file_exists_and_loads() -> None:
    assert DEFAULT_CORPUS_PATH.is_file()
    corp = load_process_reference_corpus()
    assert corp["schema_version"] == "process.parity_cases.v2"
    assert corp["corpus_status"] in {"METHOD-ONLY", "NUMERIC"}
    assert len(corp["cases"]) >= 1


def test_corpus_honesty_gate_passes() -> None:
    corp = load_process_reference_corpus()
    issues = validate_corpus_honesty(corp)
    assert issues == [], issues


def test_method_only_forbids_invented_kpis() -> None:
    corp = load_process_reference_corpus()
    case = dict(corp["cases"][0])
    case["dossier_status"] = "METHOD-ONLY"
    case["process_reference"] = {"Q_plasma": 42.0}  # invented — must fail
    bad = dict(corp)
    bad["cases"] = [case]
    issues = validate_corpus_honesty(bad)
    assert any("METHOD-ONLY" in i and "Q_plasma" in i for i in issues)


def test_corpus_dossier_hashes_match_disk() -> None:
    rep = verify_corpus_dossier_hashes()
    assert rep["ok"] is True, rep
    assert len(rep["cases"]) >= 1
    for row in rep["cases"]:
        assert row["match"] is True, row
        assert Path(row["path"]).as_posix().endswith("_delta_dossier.json")


def test_sha256_stable() -> None:
    a = sha256_hex({"b": 1, "a": 2})
    b = sha256_hex({"a": 2, "b": 1})
    assert a == b
    assert len(a) == 64
