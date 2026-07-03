# SHAMS Audit Publish Notes — 2026-07-03 (post-v412)

## Executive summary

Post-v412 audit: **148 pytest pass**, verification + golden pass. Safe v413 fixes for constraint severity gating, v401/v403 governance parity, v403 fragile margin, certification smoke. L0 proposals deferred (PROPOSAL-010–012).

## Fixes applied

- `constraint_is_hard()` + MC/nudge severity fix
- v401/v403 min-margin in `evaluate_constraints`
- v403 fragile margin `lo_key` + schema field
- v374 certification smoke test + import fallback

## Validation

- pytest: **PASS** (148)
- verification: **PASS**
- golden: **PASS**

## L0 proposals deferred

- PROPOSAL-010: unify constraint pipelines
- PROPOSAL-011: overlay `*_error` surfacing in hot_ion
- PROPOSAL-012: hot_ion import fallbacks

## PROCESS roadmap (top 3)

1. Unified constraint ledger
2. Constraint pipeline diff dossier
3. Overlay failure dashboard

Full report: `docs/validation/reports/audit_report_20260703_post_v412.md`
