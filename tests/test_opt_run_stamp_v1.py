"""Lock tests for Opt Lab ``opt_run_stamp.v1`` (Certified Optimizer 1.2)."""

from __future__ import annotations

import pytest

from src.optimization.objective_contract import from_registry_name
from src.optimization.opt_run_stamp import (
    DRIVER_CCFS_VERIFY,
    DRIVER_LHS,
    SCHEMA,
    OptRunStampError,
    build_opt_run_stamp,
    build_stamp_from_ccfs_result,
    default_ccfs_verify_contract,
    format_opt_run_stamp_summary,
    parse_opt_run_stamp,
    read_shams_version,
    stamp_ccfs_verified,
    stamp_hash,
)


def _sample(**overrides):
    contract = from_registry_name("max_Pnet", seed=7, seed_policy="fixed")
    base = dict(
        search_driver_id=DRIVER_LHS,
        n_candidates=10,
        n_verified=3,
        n_rejected=7,
        objective_contract=contract,
        seed=7,
        shams_version="test.0.0",
    )
    base.update(overrides)
    return build_opt_run_stamp(**base)


def test_schema_id_is_opt_run_stamp_v1() -> None:
    s = _sample()
    assert s.schema == SCHEMA == "opt_run_stamp.v1"
    d = s.to_dict()
    assert d["schema"] == "opt_run_stamp.v1"
    assert "stamp_sha256" in d
    assert len(d["stamp_sha256"]) == 64


def test_required_fields_present() -> None:
    d = _sample().to_dict()
    for key in (
        "schema",
        "shams_version",
        "objective_contract_hash",
        "search_driver_id",
        "n_candidates",
        "n_verified",
        "n_rejected",
        "stamp_sha256",
    ):
        assert key in d
    assert d["seed"] == 7
    assert d["search_driver_id"] == DRIVER_LHS


def test_hash_stability_identical_payloads() -> None:
    a = _sample()
    b = _sample()
    assert a.hash_sha256() == b.hash_sha256()
    assert a.to_dict()["stamp_sha256"] == b.to_dict()["stamp_sha256"]


def test_hash_changes_when_counts_or_driver_change() -> None:
    a = _sample(n_verified=3)
    b = _sample(n_verified=4, n_rejected=6)
    c = _sample(search_driver_id=DRIVER_CCFS_VERIFY)
    assert a.hash_sha256() != b.hash_sha256()
    assert a.hash_sha256() != c.hash_sha256()


def test_contract_hash_linkage() -> None:
    contract = from_registry_name("max_Pnet", seed=7, seed_policy="fixed")
    stamp = build_opt_run_stamp(
        search_driver_id=DRIVER_LHS,
        n_candidates=5,
        n_verified=1,
        n_rejected=4,
        objective_contract=contract,
        seed=7,
        shams_version="test.0.0",
    )
    assert stamp.objective_contract_hash == contract.hash_sha256()
    # Hash-only path matches object path.
    stamp2 = build_opt_run_stamp(
        search_driver_id=DRIVER_LHS,
        n_candidates=5,
        n_verified=1,
        n_rejected=4,
        objective_contract_hash=contract.hash_sha256(),
        seed=7,
        shams_version="test.0.0",
    )
    assert stamp.hash_sha256() == stamp2.hash_sha256()


def test_round_trip_parse() -> None:
    s = _sample(pack_sha256="a" * 64)
    d = s.to_dict()
    s2 = parse_opt_run_stamp(d)
    assert s2.to_dict() == d
    assert stamp_hash(d) == s.hash_sha256()


def test_parse_rejects_tampered_stamp_hash() -> None:
    d = _sample().to_dict()
    d["stamp_sha256"] = "b" * 64
    with pytest.raises(OptRunStampError, match="stamp_sha256 mismatch"):
        parse_opt_run_stamp(d)


def test_rejects_count_overflow() -> None:
    with pytest.raises(OptRunStampError, match="exceeds"):
        build_opt_run_stamp(
            search_driver_id=DRIVER_LHS,
            n_candidates=2,
            n_verified=2,
            n_rejected=1,
            objective_contract_hash="c" * 64,
            shams_version="t",
        )


def test_rejects_missing_contract() -> None:
    with pytest.raises(OptRunStampError, match="objective_contract"):
        build_opt_run_stamp(
            search_driver_id=DRIVER_LHS,
            n_candidates=1,
            n_verified=0,
            n_rejected=1,
            shams_version="t",
        )


def test_default_ccfs_contract_and_from_result() -> None:
    contract = default_ccfs_verify_contract(seed=None)
    assert contract.name == "ccfs_batch_verify"
    result = {
        "schema_version": "ccfs_verified.v1",
        "n_candidates": 4,
        "n_status_verified": 1,
        "n_status_rejected": 3,
        "verified": [],
    }
    stamp = build_stamp_from_ccfs_result(result, seed=42, shams_version="test.0.0")
    assert stamp.search_driver_id == DRIVER_CCFS_VERIFY
    assert stamp.n_candidates == 4
    assert stamp.n_verified == 1
    assert stamp.n_rejected == 3
    assert stamp.seed == 42
    assert stamp.objective_contract_hash == default_ccfs_verify_contract(seed=42).hash_sha256()

    stamped = stamp_ccfs_verified(dict(result), shams_version="test.0.0")
    assert stamped["opt_run_stamp"]["schema"] == SCHEMA
    assert stamped["opt_run_stamp"]["search_driver_id"] == DRIVER_CCFS_VERIFY


def test_pack_bytes_sets_pack_sha256() -> None:
    s = _sample(pack_bytes=b"hello-pack")
    d = s.to_dict()
    assert "pack_sha256" in d
    assert len(d["pack_sha256"]) == 64


def test_format_summary_no_version_tags() -> None:
    import re

    summary = format_opt_run_stamp_summary(_sample().to_dict())
    assert "VERIFIED=" in summary
    assert "REJECTED=" in summary
    assert "contract=" in summary
    assert not re.search(r"\bv\d{3}\b", summary)
    empty = format_opt_run_stamp_summary(None)
    assert "No opt-run stamp" in empty


def test_read_shams_version_nonempty() -> None:
    v = read_shams_version()
    assert isinstance(v, str) and len(v) > 0
