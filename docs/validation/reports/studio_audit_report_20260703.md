# SHAMS Studio Improvement Audit Report

**Date:** 2026-07-03  
**Version:** v415.0.0  
**Verdict:** approved

## Executive summary

Full studio improvement audit on `main` at v414.0.0. **157 pytest pass**, verification and golden pass. Zero test failures. Phase 3 applied **safe non-L0 fixes**: constraint ledger parity for v397/v398/v399/v403, duplicate detachment row removal, Robust Pareto Lab Evaluator choke point, timezone-aware UTC stamps. **L0 physics unchanged.** Highest remaining risk: **dual constraint pipelines** (ledger vs governance) still not fully unified — PROPOSAL-020. v399 impurity partition inside `hot_ion_point` remains a physics-governance proposal (PROPOSAL-022).

---

## 1. Inventory

### Test baseline

| Gate | Result |
|------|--------|
| `python -m pytest -q` | **PASS** (157 tests) |
| `verification/run_verification.py` | **PASS** |
| `tests/test_golden_physics_outputs.py` | **PASS** (10/10) |

**Failing tests:** none.

### Reviewer audit highlights

| Area | Finding | Severity |
|------|---------|----------|
| `constraints/system.py` vs `constraints.py` | Ledger missing v397 q0/bootstrap, v399 caps | P1 |
| `constraints/system.py` | Duplicate `detachment_index` row (v285 + v287) | P2 |
| `ui/robust_pareto_lab.py` | Direct `hot_ion_point` bypasses Evaluator AST guard | P1 |
| `ui/app.py` | Deprecated `datetime.utcnow()` | P3 |
| `hot_ion.py` | v399 impurity block inside L0 host | P0 proposal |
| `solvers/` | Some paths still call physics without Evaluator | P2 proposal |
| `certification/` | Import smoke only; no deterministic certify() regression | P2 |

### Debugger triage — no numerical failures

All failures from prior audits are closed on `main` (v410–v414). This run found **wiring/parity gaps**, not NaN regressions or golden drift.

---

## 2. Triage table

| ID | Severity | File/area | Issue | Auto-fix? | Status |
|----|----------|-----------|-------|-----------|--------|
| STU-001 | P1 | `system.py` | v397 q0/bootstrap missing in ledger | Yes | **Fixed v415** |
| STU-002 | P1 | `system.py` | v399 caps missing in ledger | Yes | **Fixed v415** |
| STU-003 | P1 | `constraints.py` | v403 granular caps governance-only | Yes | **Fixed v415** |
| STU-004 | P2 | `system.py` | Duplicate detachment_index | Yes | **Fixed v415** |
| STU-005 | P1 | `robust_pareto_lab.py` | Evaluator bypass | Yes | **Fixed v415** |
| STU-006 | P3 | `app.py`, `cert/v374` | `utcnow` deprecation | Yes | **Fixed v415** |
| STU-007 | P1 | constraint pipelines | Full unification | Proposal | PROPOSAL-020 |
| STU-008 | P1 | `hot_ion.py` | v399 impurity in L0 host | Proposal | PROPOSAL-022 |
| STU-009 | P2 | `hot_ion.py` | v399 `impurity_v399_error` key | Proposal | PROPOSAL-021 |
| STU-010 | P2 | `solvers/` | Optimizer direct physics calls | Proposal | PROPOSAL-023 |

---

## 3. Fixes applied (v415)

| File | Change |
|------|--------|
| `constraints/system.py` | v397 q0/bootstrap; v398 stability; v399 Zeff/Prad fraction/detachment; remove duplicate detachment |
| `constraints/constraints.py` | v403 granular neutronics caps (DPA, He, cooldown, TBR, attenuation) |
| `ui/robust_pareto_lab.py` | `_evaluate_point()` via `Evaluator` |
| `ui/app.py` | Timezone-aware `build_utc` |
| `certification/stability_control_certification_v374.py` | Timezone-aware certify timestamp |
| `tests/test_top5_audit_fixes.py` | v397/v399 ledger parity, detachment dedup |
| `tests/test_ui_evaluator_choke_point.py` | Robust Pareto AST guard |

**Not modified:** L0 physics equations, golden JSON, `hot_ion.py` truth path.

---

## 4. L0 / high-risk proposals (no auto-merge)

### PROPOSAL-020: Unified constraint builder (P1)

- **Files:** `constraints/system.py`, `constraints/constraints.py`, `constraints/adapters.py`
- **Problem:** Ledger and governance still built separately; parity maintained by mirroring, not single source of truth
- **Proposed fix:** One `build_all_constraints(out)` with mode adapters; diff test on every authority version
- **Golden impact:** none (wiring only)
- **Requires:** architecture review

### PROPOSAL-021: v399 overlay error surfacing (P2)

- **Files:** `hot_ion.py` v399 except block
- **Problem:** Sets `impurity_v399_validity={"error":...}` but not standardized `impurity_v399_error` for `_authority_warnings`
- **Proposed fix:** `_record_overlay_failure(..., error_key="impurity_v399_error")`
- **Requires:** explicit L0-host approval

### PROPOSAL-022: Extract v399 impurity partition from L0 (P0)

- **Files:** `hot_ion.py`, `analysis/impurity_*_v399.py`
- **Problem:** Multi-species impurity/radiation closure runs inside truth host
- **Proposed fix:** Post-truth overlay like v403/v407; truth emits Pin/P_SOL only
- **Requires:** governance version bump + golden review

### PROPOSAL-023: Solver Evaluator choke point (P2)

- **Files:** `solvers/optimize.py`, `frontier/nudges.py`, scan kits
- **Problem:** Some kits call `hot_ion_point` or ledger-only constraints
- **Proposed fix:** Mandatory `Evaluator.evaluate()` + `evaluate_constraints()` for all external optimizers
- **Golden impact:** none if wiring-only

---

## 5. Validation

| Gate | Result |
|------|--------|
| Full pytest (157) | **PASS** |
| Verification | **PASS** |
| Golden physics | **PASS** |

**Verdict:** **approved**

---

## 6. PROCESS-surpassing roadmap (ranked)

| Rank | Feature | PROCESS gap | SHAMS differentiator | L0? | Effort | Impact |
|------|---------|-------------|----------------------|-----|--------|--------|
| 1 | Unified constraint builder (PROPOSAL-020) | Inconsistent caps by workflow | Single feasibility verdict everywhere | no | M | H |
| 2 | Constraint pipeline diff dossier | Hidden dual paths | Side-by-side ledger vs governance compare UI | no | S | H |
| 3 | Overlay failure dashboard | Silent authority loss | `*_error` + `_authority_warnings` panel | yes* | S | H |
| 4 | Certification deterministic harness | No governance tier regression | `certify_*()` golden stubs v352–v395 | no | M | H |
| 5 | NO-SOLUTION mechanism atlas | Empty space suppressed | Dominant killer labeled regime maps | no | M | H |
| 6 | Verdict-first Point Designer deck | Tab sprawl | Q / feasibility / killer constraint above fold | no | M | H |
| 7 | System Suite feasibility strip | Scattered checks | One horizontal authority strip per subsystem | no | S | H |
| 8 | Mirage-safe Pareto export (v406) | Nominal-only fronts | Optimistic vs robust lanes (now Evaluator-backed) | no | S | H |
| 9 | Transport spread gate on scans | Single τE assumed | v396 spread predicate on all grid evals | no | S | H |
| 10 | SHA-256 reviewer pack + nuclear chain | No offline replay | v407/v408 provenance dossiers | no | S | H |

\* Overlay surfacing requires PROPOSAL-021 on L0 host.

**Top 3:** Unified constraint builder; constraint diff dossier; overlay failure dashboard.

---

## 7. UI improvement plan

### Phase A — Verdict-first (S, no L0)

1. **Point Designer hero strip:** feasibility verdict, dominant hard constraint, Q and nτE tier badges above tabs.
2. **System Suite feasibility strip:** horizontal chips for magnets, exhaust, neutronics, control — green/amber/red from governance constraints.
3. **Overlay failure panel:** surface all `*_error` keys and `include_*` flags from last evaluation.

### Phase B — Modular decks (M)

4. Decompose `ui/app.py` into `ui/decks/` (Point Designer, System Suite, Trade Study, Robust Pareto).
5. Expand `panel_contracts.py` with required inputs/outputs per deck.
6. Sync `physics_registry` with schema `inputs.py` field list (automated diff test).

### Phase C — Session & guardrails (M)

7. Canonical session-state API (`ui/session_api.py`) — single read/write for handoffs between decks.
8. Extend Evaluator AST guard to all `ui/*.py` modules (trade study already compliant; scan remaining bypasses).
9. Overlay authority toggle dashboard — enable/disable v396–v408 with provenance tooltips.

### Phase D — Polish (S–M)

10. Dark-mode-safe verdict colors; expandable constraint tables with residual sorting.
11. Export bundle: JSON + SHA-256 manifest from any deck run.
12. Inline “why infeasible” trace linking constraint name → output key → authority doc.

---

## 8. Physics / model recommendations (proposals only)

| ID | Recommendation | Rationale | L0? |
|----|----------------|-----------|-----|
| PHYS-001 | Wire `phase1_models` H-mode scalings into v396 envelope | Single transport authority source | no |
| PHYS-002 | Density peaking → τE proxy in v397 | Profile authority affects confinement consistently | yes |
| PHYS-003 | Expose v402 reference thresholds in schema/UI | Dominance screening currently opaque | no |
| PHYS-004 | ELM / transient heat-load overlay (v409 candidate) | Exhaust feasibility beyond steady q_div | no |
| PHYS-005 | Tritium tight closure overlay | Breeding vs inventory consistency | no |
| PHYS-006 | CD mix authority wiring to plant ledger | Auxiliary/CD electric draw traceability | no |
| PHYS-007 | Extract v399 impurity partition (PROPOSAL-022) | Keep L0 truth algebraic; radiation post-truth | yes |

---

## 9. GitHub publish

- **Branch:** `shams/studio-audit-20260703`
- **Merge:** into `main` after validation
- **Version:** v415.0.0

---

## Recommended next actions

1. Approve **PROPOSAL-020** (unified constraint builder).
2. Approve **PROPOSAL-021** (v399 error key on L0 host).
3. Schedule **PROPOSAL-022** physics review before any v399 extraction.
4. Implement UI Phase A (verdict-first strip) as next non-L0 sprint.
