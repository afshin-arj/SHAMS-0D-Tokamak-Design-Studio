# SHAMS Multi-Agent Audit Report

**Date:** 2026-07-03  
**Version:** v410.0.0  
**Verdict:** approved

## Executive summary

Post-v410 audit on `shams/audit-20260702` (PROPOSAL-002–006 merged as `5f1bc25`). **Full pytest (138 tests), verification, and golden physics pass** — zero test failures. Phase 3 applied **safe non-L0 fixes**: repo-root `analysis/_canonical_shim.py`, v408 intake unit tests, PROCESS ledger wiring for v400/v404, duplicate constraint deduplication in `system.py`, crosscode UTC deprecation fix, GOVERNANCE catalog update. **Highest open risk remains PROPOSAL-007** (v402 dominance overlay silently disabled in standard `hot_ion_point` path). Ten PROCESS-surpassing feature candidates ranked below. Phase 7 publishes branch `shams/audit-20260703` with report + fixes.

---

## 1. Inventory

### Test baseline

| Gate | Result |
|------|--------|
| `python -m pytest -q` | **PASS** (138 tests) |
| `verification/run_verification.py` | **PASS** |
| `tests/test_golden_physics_outputs.py` | **PASS** (10/10) |
| `tests/test_validation_baseline_v2230.py` | **PASS** |

**Failing tests:** none.

### Debugger root-cause — top 5 open findings (no test failures)

| Rank | ID | Root cause | Evidence |
|------|-----|------------|----------|
| 1 | PROPOSAL-007 | `hot_ion.py` uses `from ..analysis.authority_dominance_v402` which fails when `physics.hot_ion` is loaded as top-level module; bare `except` sets `include_authority_dominance_v402=False` | Manual eval: default-ON input returns `False`; isolated v402 unit test passes |
| 2 | F-011 | `system.py` accumulated duplicate `add()` rows from v226/v287 blocks re-declaring same output keys (VS/PF/RWM/exhaust) | Duplicate constraint names in PROCESS ledger for identical keys |
| 3 | F-012 | v400/v404 margins computed in `constraints.py` but absent from PROCESS ledger in `system.py` | GOVERNANCE catalog vs `build_constraints_from_outputs` gap |
| 4 | F-018 | Repo-root `src/analysis/*` shims import `analysis._canonical_shim` but shim existed only under `src/analysis/` | Direct `from src.analysis.transport_envelope_v396` import path fragile |
| 5 | F-019 | Entire `src/certification/` package (17 modules) has zero dedicated tests | Governance packs v352–v395 untested in isolation |

### Architecture smells (reviewer-equivalent readonly audit)

- Monolithic L0 host (`hot_ion.py` ~3.5k lines) with 10+ inline overlay imports
- Dual `Constraint` dataclasses (`schema.constraints` vs `constraints.constraints`)
- Split `analysis/` namespace (repo-root vs `src/analysis/`) — partial B2a reconciliation
- UI can bypass `Evaluator.evaluate()` choke point for some paths
- v402 default-ON without pipeline E2E golden pin

### Untested authority (post-fix)

| Module | Status |
|--------|--------|
| v408 intake | **Fixed** — `tests/test_nuclear_dataset_intake_v408.py` (3 tests) |
| v402 E2E pipeline | **Open** — PROPOSAL-007 |
| v384 materials lifetime | Open — golden runs disable flag |
| `src/certification/*` | Open — 17 modules, no tests |

---

## 2. Triage table

| ID | Severity | File/area | Issue | Auto-fix? | Owner |
|----|----------|-----------|-------|-----------|-------|
| PROPOSAL-007 | P1 | `hot_ion.py` L3475–3482 | v402 import fails silently | ❌ L0 guard | developer |
| F-011 | P2 | `constraints/system.py` | Duplicate constraint rows | **Fixed** | developer |
| F-012 | P2 | `constraints/system.py` | v400/v404 missing from ledger | **Fixed** | developer |
| F-018 | P2 | `analysis/_canonical_shim.py` | Missing at repo root | **Fixed** | developer |
| F-019 | P2 | `src/certification/` | Zero tests | Partial | shams-test-suite |
| F-020 | P3 | `crosscode_compare.py` | `datetime.utcnow()` deprecation | **Fixed** | developer |
| F-006–F-010 | P1 | various | PROPOSAL-002–006 | **Closed v410** | — |

---

## 3. Fixes applied

| File | Change |
|------|--------|
| `analysis/_canonical_shim.py` | **New** — repo-root shim loader for B2a canonical modules |
| `tests/test_nuclear_dataset_intake_v408.py` | **New** — metadata/CSV/roundtrip intake smoke (3 tests) |
| `src/constraints/system.py` | Add v400/v404 ledger rows; remove duplicate VS/PF/RWM/exhaust constraints |
| `benchmarks/crosscode/crosscode_compare.py` | Replace deprecated `utcnow()` with timezone-aware UTC |
| `GOVERNANCE.md` | v408 dedicated test = yes |

**Not modified:** L0 truth (`hot_ion.py`, `evaluator/`), golden JSON.

---

## 4. L0 / high-risk proposals

### PROPOSAL-001 — W prefactor

**Closed** in v409 (`b0a5ba3`).

### PROPOSAL-002 through PROPOSAL-006

**Closed** in v410 (`5f1bc25`).

### PROPOSAL-007: v402 dominance pipeline import (P1)

- **Files:** `src/physics/hot_ion.py` L3474–3482
- **Problem:** Relative import `from ..analysis.authority_dominance_v402` fails under standard test/runtime path (`physics.hot_ion`); exception handler silently disables overlay despite schema default ON
- **Proposed fix:** Add flat import fallback matching v367/v400 pattern:
  ```python
  try:
      from analysis.authority_dominance_v402 import evaluate_authority_dominance_v402
  except ImportError:
      from ..analysis.authority_dominance_v402 import evaluate_authority_dominance_v402
  ```
- **Golden impact:** yes — pin `global_dominant_authority_v402` keys if default-ON
- **Requires:** explicit user approval + `/frozen-truth-change` checklist (import wiring on L0 host file)

### PROPOSAL-008: Evaluator choke-point enforcement in UI (P2)

- **Files:** `ui/app.py`
- **Problem:** Some UI evaluation paths call `hot_ion_point` directly, bypassing `Evaluator.evaluate()` provenance stamping
- **Proposed fix:** Route all point evaluations through `Evaluator`; add import-guard test extension
- **Golden impact:** no
- **Requires:** UI refactor approval

### PROPOSAL-009: Consolidate dual Constraint types (P2)

- **Files:** `schema/constraints.py`, `constraints/constraints.py`, `constraints/system.py`
- **Problem:** Two incompatible `Constraint` dataclasses cause type confusion in forensics/solvers
- **Proposed fix:** Single public API with adapter for legacy schema consumers
- **Golden impact:** no
- **Requires:** architecture review

---

## 5. Validation

| Gate | Result |
|------|--------|
| Full pytest (138) | **PASS** |
| Verification runner | **PASS** |
| Golden physics (10) | **PASS** |
| Validation baseline v2230 | **PASS** |

**Verdict:** **approved**

See also: `.cursor/validation/reports/validation_report_20260703.md`

---

## 6. PROCESS-surpassing roadmap

| Rank | Feature | PROCESS gap | SHAMS differentiator | L0? | Effort | Impact | Next skill |
|------|---------|-------------|----------------------|-----|--------|--------|------------|
| 1 | Extopt CCFS certified-solve firewall | Optimizer mutates physics in-loop | Mandatory frozen-truth re-eval per candidate | no | M | H | `/pareto-frontier-check` |
| 2 | NO-SOLUTION mechanism-labeled regime atlas | Empty/infeasible space hidden | Infeasibility + dominant killer as first-class science | no | M | H | `/shams-feature-development` |
| 3 | Authority dominance dashboard (v402 E2E) | Killer constraint obscured in multi-physics runs | Global ranking + mirage flag when feasible-but-fragile | yes* | S | H | `/authority-overlay-author` |
| 4 | Fusion performance tier ledger | Nominal Q only in scans | Q, nτE, H98 tiers with NO-SOLUTION attribution | no | M | H | `/point-design-eval` |
| 5 | Mirage-safe Pareto export (v406 lanes) | Nominal-only Pareto fronts | Optimistic vs robust lane separation + mirage filter | no | S | H | `/pareto-frontier-check` |
| 6 | SHA-256 reviewer pack + nuclear provenance | No offline replay dossier | v407/v408 pinned dataset chain + manifest | no | S | H | `/reviewer-pack-export` |
| 7 | Automated PROCESS parity delta dossier | Manual cross-code compare | Deterministic KPI constitution diff (`parity_harness`) | no | M | H | `/reviewer-pack-export` |
| 8 | Transport envelope spread gate on scans | Single τE scaling assumed | v396 spread-ratio predicate on scan grids | no | S | H | `/transport-specialist` |
| 9 | Policy-tier constraint explorer UI | Hard limits only | Hard vs diagnostic q95/Greenwald with provenance stamp | no | M | M | `/shams-feature-development` |
| 10 | Certification pack regression harness | No governance tier testing | Deterministic tier packs v352–v395 with golden stubs | no | L | M | `/shams-test-suite` |

\* v402 requires PROPOSAL-007 import wiring on L0 host (governance-only overlay merge).

**Top 3:** CCFS firewall; NO-SOLUTION atlas; v402 dominance dashboard (after PROPOSAL-007).

---

## 7. GitHub publish

- **Branch:** `shams/audit-20260703`
- **Base:** `main` (v410 on audit branch via merge)
- **Commit:** audit safe fixes + reports (this run)
- **PR:** Open into `main` (GitHub UI or `gh` when available)
- **Files committed:** fixes listed in §3, audit reports; not runtime artifacts

---

## Recommended next actions

1. Approve **PROPOSAL-007** (v402 import fallback) + optional golden pin for dominance keys.
2. Add certification pack smoke tests (PROPOSAL-010 seed).
3. Merge audit branch to `main` after PR review.
