# SHAMS Multi-Agent Audit Report

**Date:** 2026-07-03 (post-v412)  
**Version:** v413.0.0  
**Verdict:** approved

## Executive summary

Post-v412 audit on `main` at v412.0.0. **145 → 148 pytest pass**, verification and golden pass. Zero test failures. Phase 3 applied **safe non-L0 fixes**: constraint severity gating, v401/v403 governance parity, v403 fragile margin wiring, certification smoke test, import fallbacks. **Highest open risk: dual constraint pipelines** (ledger vs governance) still diverge on v396/v397/v384 caps (PROPOSAL-010). Silent overlay failures in `hot_ion.py` remain L0-guard proposals.

---

## 1. Inventory

### Test baseline

| Gate | Result |
|------|--------|
| `python -m pytest -q` | **PASS** (148 tests) |
| `verification/run_verification.py` | **PASS** |
| `tests/test_golden_physics_outputs.py` | **PASS** (10/10) |
| `tests/test_validation_baseline_v2230.py` | **PASS** |

**Failing tests:** none.

### Debugger root-cause — top 5 open findings (no test failures)

| Rank | ID | Root cause | Evidence |
|------|-----|------------|----------|
| 1 | AUD-001 / PROPOSAL-010 | `build_constraints_from_outputs` vs `evaluate_constraints` enforce **different** authority caps depending on caller | Optimizers use ledger; Systems/UQ use governance |
| 2 | AUD-003 / PROPOSAL-011 | Overlay `except` blocks in `hot_ion.py` set `include_*=False` without `*_error` keys | `_authority_warnings` stays empty when overlay fails |
| 3 | AUD-005 / PROPOSAL-012 | Bare `from src.contracts.*` / `from src.analysis.*` in `hot_ion.py` without fallback | Breaks under `src/`-only `sys.path` layouts |
| 4 | AUD-002 | **Fixed** — `getattr(c,"hard",True)` ignored `severity="soft"` on `GovernanceConstraint` | MC feasibility over-counted failures |
| 5 | AUD-012 | `src/certification/` (17 modules) had zero tests | **Partial fix** — v374 smoke added |

### Closed since v412

- PROPOSAL-007 (v402 import) — **closed v411**
- PROPOSAL-008 (UI choke point) — **closed v412**
- PROPOSAL-009 (constraint API) — **closed v412**

---

## 2. Triage table

| ID | Severity | File/area | Issue | Auto-fix? | Status |
|----|----------|-----------|-------|-----------|--------|
| AUD-002 | P1 | `optimize.py`, `nudges.py` | Soft constraints treated as hard | Yes | **Fixed v413** |
| AUD-004 | P1 | `system.py` | v403 margin no `lo_key` | Yes | **Fixed v413** |
| AUD-009 | P2 | `constraints.py` | Missing v401/v403 in governance | Partial | **Fixed v413** |
| AUD-007 | P2 | `system.py` | Duplicate TF peak field name | Yes | **Fixed v413** |
| AUD-014 | P2 | `evaluator/core.py` | Dead import branch | Yes | **Fixed v413** |
| AUD-013 | P2 | `certification/v374` | Hard `src.physics` imports | Yes | **Fixed v413** |
| AUD-012 | P2 | `certification/` | Zero tests | Partial | **v374 smoke v413** |
| AUD-001 | P1 | constraint pipelines | Divergent builders | Proposal | PROPOSAL-010 |
| AUD-003 | P1 | `hot_ion.py` | Silent overlay loss | Proposal | PROPOSAL-011 |
| AUD-005 | P1 | `hot_ion.py` | Import path fragility | Proposal | PROPOSAL-012 |
| AUD-006 | P2 | `analysis/` split tree | B2a reconciliation incomplete | Design | Deferred |
| AUD-010 | P2 | `system.py` | Missing v396/v397/v384 ledger caps | Partial | Deferred |

---

## 3. Fixes applied (v413)

| File | Change |
|------|--------|
| `constraints/constraints.py` | `constraint_is_hard()`; v401/v403 `ge()` blocks |
| `constraints/system.py` | v403 `lo_key`; rename TF peak field (v288) |
| `solvers/optimize.py`, `frontier/nudges.py` | Use `constraint_is_hard()` |
| `schema/inputs.py` | `nm_fragile_margin_frac_v403` |
| `analysis/neutronics_materials_library_v403.py` | Echo fragile margin to outputs |
| `evaluator/core.py` | Clean import fallback |
| `certification/stability_control_certification_v374.py` | Dual physics imports |
| `tests/test_constraint_severity.py` | **New** |
| `tests/test_certification_smoke_v374.py` | **New** |

**Not modified:** L0 physics equations, golden JSON.

---

## 4. L0 / high-risk proposals

### PROPOSAL-010: Unify constraint pipelines (P1)

- **Files:** `constraints/system.py`, `constraints/constraints.py`
- **Problem:** Same point can be feasible in one mode and infeasible in another
- **Proposed fix:** Single builder + adapters, or symmetric mirror of v396/v397/v384 ↔ v401/v403/v407 blocks
- **Golden impact:** no (wiring only)
- **Requires:** architecture review

### PROPOSAL-011: Overlay failure surfacing in hot_ion (P1)

- **Files:** `hot_ion.py` overlay except blocks
- **Problem:** Silent `include_*=False` without `*_error` keys
- **Proposed fix:** Set `"<overlay>_error": str(e)` in except paths (governance wiring only)
- **Requires:** explicit L0-host file approval

### PROPOSAL-012: hot_ion import fallbacks (P1)

- **Files:** `hot_ion.py` L3217–3334
- **Problem:** Bare `from src.*` imports fail under alternate entrypoints
- **Proposed fix:** Match v400/v402 dual-import pattern throughout
- **Requires:** explicit L0-host file approval

---

## 5. Validation

| Gate | Result |
|------|--------|
| Full pytest (148) | **PASS** |
| Verification | **PASS** |
| Golden physics | **PASS** |

**Verdict:** **approved**

---

## 6. PROCESS-surpassing roadmap

| Rank | Feature | PROCESS gap | SHAMS differentiator | L0? | Effort | Impact |
|------|---------|-------------|----------------------|-----|--------|--------|
| 1 | Unified constraint ledger | Inconsistent caps by workflow | Single feasibility verdict everywhere | no | M | H |
| 2 | Constraint pipeline diff dossier | Hidden dual paths | Side-by-side ledger vs governance compare | no | S | H |
| 3 | Overlay failure dashboard | Silent authority loss | `*_error` + `_authority_warnings` UI panel | yes* | S | H |
| 4 | Certification pack regression harness | No governance tier tests | Deterministic v352–v395 smoke + golden stubs | no | M | H |
| 5 | NO-SOLUTION mechanism atlas | Empty space suppressed | Dominant killer labeled regime maps | no | M | H |
| 6 | Fusion performance tier ledger | Nominal Q only | Q / nτE / H98 tiers + NO-SOLUTION | no | M | H |
| 7 | Mirage-safe Pareto export (v406) | Nominal-only fronts | Optimistic vs robust lanes | no | S | H |
| 8 | Extopt CCFS certified-solve firewall | Optimizer mutates physics | Mandatory frozen-truth re-eval | no | M | H |
| 9 | Transport spread gate on scans | Single τE assumed | v396 spread predicate on grids | no | S | H |
| 10 | SHA-256 reviewer pack + nuclear chain | No offline replay | v407/v408 provenance dossiers | no | S | H |

\* Overlay surfacing requires PROPOSAL-011 on L0 host imports only.

**Top 3:** Unified constraint ledger; constraint pipeline diff dossier; overlay failure dashboard.

---

## 7. GitHub publish

- **Branch:** `shams/audit-20260703-v413`
- **Merge:** into `main` after validation
- **Files:** v413 fixes + this report

---

## Recommended next actions

1. Approve **PROPOSAL-010** (constraint pipeline unification).
2. Approve **PROPOSAL-011** + **PROPOSAL-012** (hot_ion governance wiring batch).
3. Expand certification smoke tests beyond v374.
