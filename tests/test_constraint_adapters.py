from __future__ import annotations

from schema.constraints import LedgerConstraint
from constraints.adapters import governance_from_ledger, ledger_from_governance
from constraints.constraints import GovernanceConstraint


def test_ledger_from_governance_le() -> None:
    g = GovernanceConstraint(
        name="betaN",
        value=2.5,
        limit=3.0,
        sense="<=",
        passed=True,
        units="-",
        note="screening",
    )
    l = ledger_from_governance(g)
    assert isinstance(l, LedgerConstraint)
    assert l.name == "betaN"
    assert l.hi == 3.0
    assert l.lo is None
    assert l.ok is True


def test_ledger_from_governance_ge() -> None:
    g = GovernanceConstraint(
        name="q95",
        value=4.0,
        limit=3.0,
        sense=">=",
        passed=True,
        units="-",
    )
    l = ledger_from_governance(g)
    assert l.lo == 3.0
    assert l.hi is None
    assert l.ok is True


def test_governance_from_ledger_roundtrip_le() -> None:
    g0 = GovernanceConstraint(
        name="P_SOL",
        value=80.0,
        limit=100.0,
        sense="<=",
        passed=True,
        units="MW",
        note="exhaust",
    )
    l = ledger_from_governance(g0)
    g1 = governance_from_ledger(l)
    assert g1.name == g0.name
    assert g1.value == g0.value
    assert g1.limit == g0.limit
    assert g1.sense == g0.sense
    assert g1.passed == g0.passed


def test_public_api_exports() -> None:
    import constraints as cs

    assert hasattr(cs, "LedgerConstraint")
    assert hasattr(cs, "GovernanceConstraint")
    assert hasattr(cs, "ledger_from_governance")
    assert hasattr(cs, "governance_from_ledger")
    assert cs.LegacyConstraint is cs.LedgerConstraint
