# Explicit Failure Event Schema (v69 upgrade)
**Generated:** 2026-01-07

This schema standardizes machine-readable solver/UI outcomes.
It **does not** change solver behavior; it only constrains reporting.

## Required fields (all events)
- `event_type`: string
- `timestamp`: ISO 8601
- `ui_mode`: one of `Point|Systems|Scan|Pareto`
- `run_id`: string (stable within a run)
- `message`: human-readable summary
- `provenance`: object (version tag, git hash if available, inputs snapshot path)

## Standard event types
### `precheck_infeasible`
Emitted when feasibility-first precheck proves targets are impossible given constraints.

### `continuation_step`
Emitted per continuation ramp step.
Fields: `cont_step`, `targets`, `current`, `cont_result`

### `continuation_stall`
Emitted when continuation cannot make progress.
Fields: `cont_step`, `reason`

### `max_iter_exceeded`
Emitted when solver hits `max_iter`.

### `constraint_violation`
Emitted when constraints cannot be satisfied.
Fields: `violated_constraints[]`

### `converged`
Emitted on successful convergence.
Fields: `iters`, `residual_norm`, `constraints_ok: true`
