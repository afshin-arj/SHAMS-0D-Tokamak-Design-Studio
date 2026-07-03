# PATCH NOTES — v416.0.0

## v416.0.0 — PROPOSAL-020–023 + UI Phases A–D

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-020 — Unified constraint builder

- `constraints/unified.py`: `build_all_constraints()`, `ConstraintBundle`, `diff_constraint_pipelines()`.
- Public API exported from `constraints/__init__.py`.

### PROPOSAL-021 / PROPOSAL-022 — v399 post-truth overlay

- Extracted v399 impurity partition from inline L0 block to `analysis/impurity_radiation_v399.py::evaluate_impurity_radiation_authority_v399`.
- `hot_ion.py`: overlay runs before v402 dominance; `impurity_v399_error` via `_record_overlay_failure`.
- Golden outputs unchanged (ordering preserved for v402).

### PROPOSAL-023 — Solver Evaluator choke point

- `solvers/evaluator_bridge.py`: shared `evaluate_point()` for optimizers.
- `solvers/optimize.py`, `frontier/nudges.py`: route through Evaluator.

### UI Phases A–D

- `ui/verdict_ui.py`: hero strip, feasibility chips, overlay panel, sorted constraint table.
- `ui/session_api.py`, `ui/export_bundle.py`, `ui/constraint_trace.py`, `ui/authority_dashboard.py`.
- `ui/decks/`: Point Designer and System Suite hook modules.
- `ui/app.py`: integrated hero strip, authority dashboard, trace, export, constraint table.
- `panel_contracts.py`: deck contracts expanded.
- `tests/test_ui_evaluator_guard_all.py`: AST guard for all `ui/*.py`.

### Tests

- `test_unified_constraints.py`, `test_v399_overlay_extraction.py`, `test_solver_evaluator_choke.py`, `test_physics_registry_sync.py`.
