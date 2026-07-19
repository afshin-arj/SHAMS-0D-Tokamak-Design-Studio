"""Lock tests for Opt Lab ``objective_contract.v1`` (Certified Optimizer 0.1)."""

from __future__ import annotations

import pytest

from src.optimization.objective_contract import (
    SCHEMA,
    ObjectiveContractError,
    build_objective_contract,
    contract_hash,
    from_registry_name,
    list_registry_contract_names,
    parse_objective_contract,
)

# SHA-256 of canonical JSON for the golden sample in test_golden_hash_example_lock.
# Update only when objective_contract.v1 canonical form intentionally changes.
_KNOWN_MAX_PNET_FIXED0_HASH = (
    "420ecc57193279b7aa1f961bd1a984ee7ee7d53fc8269989a9804a0b52f116c1"
)


def _sample(**overrides):
    base = {
        "name": "max_Pnet",
        "sense": "max",
        "metric_keys": ["P_e_net_MW"],
        "bounds_policy": "user_supplied",
        "seed_policy": "required",
        "notes": "maximize net electric power",
    }
    base.update(overrides)
    return build_objective_contract(**base)


def test_schema_id_is_objective_contract_v1() -> None:
    c = _sample()
    assert c.schema == SCHEMA == "objective_contract.v1"
    assert c.to_dict()["schema"] == "objective_contract.v1"


def test_round_trip_serialize_parse() -> None:
    c = _sample(seed=42, seed_policy="fixed", provenance={"source": "unit_test"})
    d = c.to_dict()
    c2 = parse_objective_contract(d)
    assert c2.to_dict() == d
    assert c2.hash_sha256() == c.hash_sha256()


def test_hash_stability_identical_payloads() -> None:
    a = _sample(seed=7, seed_policy="fixed")
    b = _sample(seed=7, seed_policy="fixed")
    assert a.hash_sha256() == b.hash_sha256()
    payload = a.to_dict()
    shuffled = {
        "notes": payload["notes"],
        "schema": payload["schema"],
        "seed": payload["seed"],
        "name": payload["name"],
        "bounds_policy": payload["bounds_policy"],
        "seed_policy": payload["seed_policy"],
        "sense": payload["sense"],
        "metric_keys": payload["metric_keys"],
    }
    assert contract_hash(shuffled) == a.hash_sha256()


def test_hash_changes_when_sense_changes() -> None:
    a = _sample(sense="max")
    b = _sample(sense="min")
    assert a.hash_sha256() != b.hash_sha256()


def test_hash_changes_when_metric_changes() -> None:
    a = _sample(metric_keys=["P_e_net_MW"])
    b = _sample(metric_keys=["R0_m"])
    assert a.hash_sha256() != b.hash_sha256()


def test_hash_changes_when_bounds_or_seed_policy_changes() -> None:
    a = _sample(bounds_policy="user_supplied", seed_policy="required")
    b = _sample(bounds_policy="driver_default", seed_policy="required")
    c = _sample(bounds_policy="user_supplied", seed_policy="optional")
    assert a.hash_sha256() != b.hash_sha256()
    assert a.hash_sha256() != c.hash_sha256()


def test_rejects_empty_name() -> None:
    with pytest.raises(ObjectiveContractError, match="name"):
        build_objective_contract(
            name="  ",
            sense="min",
            metric_keys=["R0_m"],
        )


def test_rejects_invalid_sense() -> None:
    with pytest.raises(ObjectiveContractError, match="sense"):
        build_objective_contract(
            name="x",
            sense="optimize",
            metric_keys=["R0_m"],
        )


def test_rejects_empty_or_duplicate_metric_keys() -> None:
    with pytest.raises(ObjectiveContractError, match="metric_keys"):
        build_objective_contract(name="x", sense="min", metric_keys=[])
    with pytest.raises(ObjectiveContractError, match="duplicate"):
        build_objective_contract(
            name="x", sense="min", metric_keys=["R0_m", "R0_m"]
        )


def test_rejects_invalid_bounds_and_seed_policy() -> None:
    with pytest.raises(ObjectiveContractError, match="bounds_policy"):
        build_objective_contract(
            name="x",
            sense="min",
            metric_keys=["R0_m"],
            bounds_policy="soft",
        )
    with pytest.raises(ObjectiveContractError, match="seed_policy"):
        build_objective_contract(
            name="x",
            sense="min",
            metric_keys=["R0_m"],
            seed_policy="randomish",
        )


def test_rejects_fixed_seed_without_value() -> None:
    with pytest.raises(ObjectiveContractError, match="seed"):
        build_objective_contract(
            name="x",
            sense="min",
            metric_keys=["R0_m"],
            seed_policy="fixed",
            seed=None,
        )


def test_rejects_wrong_schema() -> None:
    with pytest.raises(ObjectiveContractError, match="schema"):
        parse_objective_contract(
            {
                "schema": "objective_contract.v3",
                "name": "x",
                "sense": "min",
                "metric_keys": ["R0_m"],
                "bounds_policy": "user_supplied",
                "seed_policy": "required",
            }
        )


def test_from_registry_name_resolves_legacy_fom() -> None:
    c = from_registry_name("max_Pnet", seed_policy="fixed", seed=1)
    assert c.name == "max_Pnet"
    assert c.sense == "max"
    assert c.metric_keys == ("P_e_net_MW",)
    assert c.primary_metric_key() == "P_e_net_MW"
    assert c.notes  # description from ObjectiveSpec


def test_from_registry_unknown_rejected() -> None:
    with pytest.raises(ObjectiveContractError, match="unknown"):
        from_registry_name("not_a_real_fom")


def test_registry_bridge_covers_defaults() -> None:
    names = list_registry_contract_names()
    assert "min_R0" in names
    assert "max_Q" in names
    for name in names:
        c = from_registry_name(name)
        assert c.schema == SCHEMA
        assert c.metric_keys
        assert c.sense in ("min", "max")


def test_golden_hash_example_lock() -> None:
    """Pinned hash for a canonical sample — drift fails the lock."""
    c = build_objective_contract(
        name="max_Pnet",
        sense="max",
        metric_keys=["P_e_net_MW"],
        bounds_policy="user_supplied",
        seed_policy="fixed",
        seed=0,
        notes="",
    )
    assert len(c.hash_sha256()) == 64
    assert c.hash_sha256() == _KNOWN_MAX_PNET_FIXED0_HASH
    assert parse_objective_contract(c.to_dict()).hash_sha256() == _KNOWN_MAX_PNET_FIXED0_HASH
