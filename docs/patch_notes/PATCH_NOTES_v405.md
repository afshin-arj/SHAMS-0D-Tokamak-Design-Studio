# PATCH NOTES — v405.0.0

**Release:** v405.0.0

**Title:** Certified Search Orchestrator 3.0 (Feasible-first Pareto + Lane Evidence Packs)

## What changed

### 1) Certified Search Orchestrator 3.0 (solver layer)

- Added a **Pareto frontier mode** that:
  - generates deterministic candidate sets using the existing staged budgeted search,
  - evaluates each candidate with the frozen evaluator,
  - extracts a feasible-first **nondominated frontier** under declared objectives.

- Added **lane evaluation** for frontier candidates:
  - *Optimistic lane* uses `optimistic_uncertainty_contract()`
  - *Robust lane* uses `robust_uncertainty_contract()`
  - Both are evaluated via deterministic corner enumeration (`run_uncertainty_contract_for_point`).

- Added **lane-mirage detection** (`optimistic == ROBUST_PASS` while `robust != ROBUST_PASS`).

### 2) UI integration (Control Room → Certified Search)

- Added a **Mode** selector:
  - *Single objective (v340 compat)*: keeps the existing behavior.
  - *Pareto frontier (v405)*: enables multi-objective frontier extraction.

- Added a **Frontier candidates table** and a **per-candidate evidence pack export**.

### 3) Evidence pack determinism

- `tools/simple_evidence_zip.py` no longer injects wall-clock timestamps by default.
- Added `tools/frontier_candidate_evidence_zip.py` for deterministic per-candidate packs.

## Compatibility

- The previous orchestrator entrypoint `run_orchestrated_certified_search()` remains available.
- Orchestrator evidence schema is bumped to `certified_search_orchestrator_evidence.v3`.

## Architectural compliance

- Frozen Truth Law preserved (no solvers / iteration / smoothing inside truth).
- Exploration remains budgeted, deterministic, and auditable.
