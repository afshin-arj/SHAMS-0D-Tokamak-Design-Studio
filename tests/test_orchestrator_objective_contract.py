from __future__ import annotations

import pytest


def test_objective_contract_v3_validation_smoke() -> None:
    from src.extopt.orchestrator import _validate_objective_contract

    keys, senses = _validate_objective_contract(
        {
            "schema": "objective_contract.v3",
            "objectives": [
                {"key": "P_e_net_MW", "sense": "max"},
                {"key": "B_peak_T", "sense": "min"},
            ],
            "selection": {"ordering": ["worst_hard_margin", "objective"]},
        }
    )
    assert keys == ["P_e_net_MW", "B_peak_T"]
    assert senses["P_e_net_MW"] == "max"
    assert senses["B_peak_T"] == "min"


def test_objective_contract_rejects_duplicate_keys() -> None:
    from src.extopt.orchestrator import _validate_objective_contract

    with pytest.raises(ValueError):
        _validate_objective_contract(
            {
                "schema": "objective_contract.v3",
                "objectives": [
                    {"key": "P_e_net_MW", "sense": "max"},
                    {"key": "P_e_net_MW", "sense": "max"},
                ],
            }
        )
