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
from .constraints import Constraint, GovernanceConstraint, constraint_is_hard, evaluate_constraints
from .registry import ConstraintKind, ConstraintRegistry, ConstraintSpec
from .system import build_constraints_from_outputs, summarize_constraints
from .unified import ConstraintBundle, build_all_constraints, diff_constraint_pipelines, dominant_failing_constraint
from .authority_registry import (
    evaluate_registry_governance,
    evaluate_registry_ledger,
    load_authority_specs,
    registry_spec_names,
)
from .registry_codegen import generate_registry_module, verify_codegen_sync

# Backward-compatible alias for schema ledger type.
LegacyConstraint = LedgerConstraint

__all__ = [
    "Constraint",
    "GovernanceConstraint",
    "constraint_is_hard",
    "LedgerConstraint",
    "LegacyConstraint",
    "evaluate_constraints",
    "build_constraints_from_outputs",
    "summarize_constraints",
    "build_all_constraints",
    "ConstraintBundle",
    "diff_constraint_pipelines",
    "dominant_failing_constraint",
    "load_authority_specs",
    "evaluate_registry_governance",
    "evaluate_registry_ledger",
    "generate_registry_module",
    "verify_codegen_sync",
    "ledger_from_governance",
    "governance_from_ledger",
    "ConstraintRegistry",
    "ConstraintSpec",
    "ConstraintKind",
]
