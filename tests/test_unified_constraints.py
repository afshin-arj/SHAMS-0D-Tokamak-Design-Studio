from __future__ import annotations

from constraints.unified import build_all_constraints, diff_constraint_pipelines
from constraints.constraints import evaluate_constraints
from constraints.system import build_constraints_from_outputs


def test_build_all_constraints_returns_both_pipelines() -> None:
    out = {
        "Q_DT_eqv": 5.0,
        "beta_N": 2.0,
        "betaN_max": 3.0,
        "transport_spread_ratio_v396": 1.2,
        "transport_spread_max_v396": 1.5,
    }
    bundle = build_all_constraints(out)
    assert len(bundle.governance) >= 1
    assert len(bundle.ledger) >= 1
    assert "n_governance" in bundle.parity
    assert "n_ledger" in bundle.parity


def test_diff_constraint_pipelines_detects_mismatch() -> None:
    from constraints.constraints import GovernanceConstraint

    gov = [
        GovernanceConstraint(
            name="Test cap",
            value=2.0,
            limit=1.0,
            sense="<=",
            passed=False,
            units="-",
        )
    ]
    led = build_constraints_from_outputs({"beta_N": 2.0, "betaN_max": 3.0})
    diff = diff_constraint_pipelines(gov, led)
    assert diff["n_governance"] == 1
    assert diff["n_ledger"] >= 0
