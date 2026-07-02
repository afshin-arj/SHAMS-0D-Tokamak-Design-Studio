# SHAMS Release Validation Report

**Validation ID:** VAL-20260703-AUDIT  
**Timestamp:** 2026-07-03  
**Physics Model Version:** v410.0.0  
**Validation Status:** **approved**

---

## Regression tests

| Command | Result |
|---------|--------|
| `python -m pytest -q` | PASS (138 tests) |
| `tests/test_golden_physics_outputs.py` | PASS (10/10) |
| `tests/test_validation_baseline_v2230.py` | PASS |

---

## Verification runner

| Command | Result |
|---------|--------|
| `python verification/run_verification.py` | PASS |
| IMPORT_POLICY_OK | yes |
| Physics benchmarks | PASS |

---

## Constraint review (readonly)

| Constraint | Status |
|------------|--------|
| Greenwald | Wired via `fG` / diagnostic policy tier |
| Troyon βN | Wired post-v410 (`betaN_proxy`, `beta_N`) |
| Power balance | Residual constraint when tol set |

---

## Golden drift

No drift detected. v410 golden regeneration already merged on audit branch.

---

## Reviewer notes

- L0 truth unchanged in this audit run.
- Open P1: PROPOSAL-007 (v402 pipeline import) — proposal only, not in this commit.
- Safe fixes: constraint ledger hygiene, v408 tests, canonical shim, crosscode UTC.

**Verdict:** **approved**
