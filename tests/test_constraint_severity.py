from __future__ import annotations

from constraints.constraints import GovernanceConstraint, constraint_is_hard


def test_constraint_is_hard_respects_severity() -> None:
    hard = GovernanceConstraint(
        name="q95",
        value=3.5,
        limit=3.0,
        sense=">=",
        passed=True,
        severity="hard",
    )
    soft = GovernanceConstraint(
        name="q95_diag",
        value=2.5,
        limit=3.0,
        sense=">=",
        passed=False,
        severity="soft",
    )
    assert constraint_is_hard(hard) is True
    assert constraint_is_hard(soft) is False


def test_governance_v403_margin_enforced_when_fragile_key_present() -> None:
    from constraints.constraints import evaluate_constraints

    out = {
        "nm_min_margin_frac_v403": 0.05,
        "nm_fragile_margin_frac_v403": 0.10,
    }
    cons = evaluate_constraints(out)
    names = {c.name for c in cons}
    assert "NM library min margin (v403)" in names
    row = next(c for c in cons if c.name == "NM library min margin (v403)")
    assert row.passed is False
