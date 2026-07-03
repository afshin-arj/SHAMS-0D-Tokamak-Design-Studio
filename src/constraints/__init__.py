"""Public constraint API (PROPOSAL-009).

- ``LedgerConstraint``: schema PROCESS ledger record (lo/hi/ok)
- ``GovernanceConstraint``: rich governance cartography record
- ``Constraint``: backward-compatible alias for ``GovernanceConstraint``
"""
from __future__ import annotations

try:
    from schema.constraints import Constraint as LedgerConstraint  # type: ignore
except ImportError:
    from src.schema.constraints import Constraint as LedgerConstraint  # type: ignore

from .adapters import governance_from_ledger, ledger_from_governance
from .constraints import Constraint, GovernanceConstraint, evaluate_constraints
from .registry import ConstraintKind, ConstraintRegistry, ConstraintSpec
from .system import build_constraints_from_outputs, summarize_constraints

# Backward-compatible alias for schema ledger type.
LegacyConstraint = LedgerConstraint

__all__ = [
    "Constraint",
    "GovernanceConstraint",
    "LedgerConstraint",
    "LegacyConstraint",
    "evaluate_constraints",
    "build_constraints_from_outputs",
    "summarize_constraints",
    "ledger_from_governance",
    "governance_from_ledger",
    "ConstraintRegistry",
    "ConstraintSpec",
    "ConstraintKind",
]
