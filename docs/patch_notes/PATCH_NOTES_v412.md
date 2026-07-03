# PATCH NOTES — v412.0.0

## v412.0.0 — PROPOSAL-008 & PROPOSAL-009 (UI choke point + constraint API)

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-008 — Evaluator choke-point enforcement in UI

- `ui/app.py`: route point evaluation through `_ui_evaluate()` → `Evaluator.evaluate()` for audit, envelope scan, run artifacts, scan grids, certified search, Pareto v405, Jacobian FD, corner probes, and Systems point checks.
- Single documented bypass: golden JSON regen tool uses raw `hot_ion_point` for parity with `tests/test_golden_physics_outputs.py`.
- `tests/test_ui_evaluator_choke_point.py` — AST guard for unapproved direct truth calls.

### PROPOSAL-009 — Consolidate dual Constraint types

- `schema.constraints`: explicit `LedgerConstraint` alias (PROCESS ledger: lo/hi/ok).
- `constraints.constraints`: rename to `GovernanceConstraint`; `Constraint` remains backward-compatible alias.
- `constraints/adapters.py`: `ledger_from_governance` / `governance_from_ledger`.
- `constraints/__init__.py`: unified public API exports both types + adapters.
- `constraints/system.py`, `analysis/forensics.py`: import `LedgerConstraint` explicitly.

No golden regeneration required (no physics or default output-key changes).
