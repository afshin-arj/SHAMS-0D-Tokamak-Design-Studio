"""Adapters between PROCESS ledger and governance constraint records (PROPOSAL-009)."""
from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from schema.constraints import Constraint as LedgerConstraint  # type: ignore
except ImportError:
    from src.schema.constraints import Constraint as LedgerConstraint  # type: ignore

from .constraints import GovernanceConstraint

if TYPE_CHECKING:
    pass


def ledger_from_governance(c: GovernanceConstraint) -> LedgerConstraint:
    """Map a governance constraint to the schema ledger representation."""
    sense = str(c.sense).strip()
    if sense == "<=":
        return LedgerConstraint(
            name=c.name,
            value=float(c.value),
            lo=None,
            hi=float(c.limit),
            units=str(c.units or "-"),
            description=str(c.note or c.meaning or ""),
        )
    return LedgerConstraint(
        name=c.name,
        value=float(c.value),
        lo=float(c.limit),
        hi=None,
        units=str(c.units or "-"),
        description=str(c.note or c.meaning or ""),
    )


def governance_from_ledger(c: LedgerConstraint) -> GovernanceConstraint:
    """Map a schema ledger constraint to the governance cartography type."""
    if c.hi is not None and c.lo is None:
        sense = "<="
        limit = float(c.hi)
    elif c.lo is not None and c.hi is None:
        sense = ">="
        limit = float(c.lo)
    elif c.hi is not None and c.lo is not None:
        sense = "<="
        limit = float(c.hi)
    else:
        sense = ">="
        limit = float(c.value)
    return GovernanceConstraint(
        name=c.name,
        value=float(c.value),
        limit=limit,
        sense=sense,
        passed=bool(c.ok),
        units=str(c.units or "-"),
        note=str(c.description or ""),
    )
