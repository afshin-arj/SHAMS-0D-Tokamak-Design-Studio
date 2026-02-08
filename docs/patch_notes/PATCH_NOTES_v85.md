# PATCH NOTES — v85 (2026-01-08)

v85 introduces a **SAFE Optimizer Sandbox** accessible from the same UI **after** SHAMS feasibility work.

## Added
- Optimization Sandbox tab in UI (non-authoritative ranking)
- Sandbox CLI: `python -m tools.sandbox.sandbox_optimize`
- Objective ranking over SHAMS-feasible datasets only
- Mandatory non-authoritative labeling + manifest hashing
- Default re-audit of Top-10 (when inputs are present in feasible_scan records)
- Feasible Scan export now includes `inputs` payload for provenance and re-audit

## Unchanged
- Physics evaluator
- Solver logic / continuation behavior
- Default execution paths
