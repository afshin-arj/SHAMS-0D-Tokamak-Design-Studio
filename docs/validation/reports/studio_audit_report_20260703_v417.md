# SHAMS Studio Improvement Audit Report

**Date:** 2026-07-03 (post-v416)  
**Version:** v417.0.0  
**Verdict:** approved

## Executive summary

Implemented **PROPOSAL-024–025** and **PHYS-002** (approved L0) plus **PHYS-004–006** authority overlays. **176 pytest pass**, verification and golden pass. Constraint registry is now single-source JSON; certification modules have deterministic digest harness; v397 density peaking couples to τE when profile proxy is enabled; v408/v409/v405 overlays and registry caps are live.

---

## 1. Inventory

| Gate | Result |
|------|--------|
| `python -m pytest -q` | **PASS** (176 tests) |
| `verification/run_verification.py` | **PASS** |
| Golden physics | **PASS** (10/10, regen for additive CD-mix keys) |

**Failing tests:** none (after `__pycache__` hygiene cleanup).

### Closed proposals

| ID | Status |
|----|--------|
| PROPOSAL-024 | **Closed v417** — certification deterministic harness |
| PROPOSAL-025 | **Closed v417** — `authority_caps.json` + registry evaluator |
| PHYS-002 | **Closed v417** — density peaking → τE in v397 (L0) |
| PHYS-004 | **Closed v417** — ELM transient heat overlay v409 |
| PHYS-005 | **Closed v417** — tritium tight-closure registry + shim |
| PHYS-006 | **Closed v417** — CD mix plant ledger v408 |

---

## 2. Triage — remaining open items

| ID | Severity | Issue | Status |
|----|----------|-------|--------|
| STU-020 | P2 | Ledger/governance parity not 100% (only_* sets non-empty) | Monitor via `bundle.parity` |
| STU-022 | P2 | Full `app.py` deck decomposition | Incremental |
| STU-023 | P2 | Registry not yet code-generated into constraint modules | PROPOSAL-026 |
| STU-024 | P3 | `__pycache__` hygiene on dev machines | Local cleanup |
| PHYS-003 | P2 | v402 reference thresholds not in schema/UI | Proposal |
| PHYS-008 | P2 | `phase1_models` H-mode not wired to v396 envelope | Proposal |

**Debugger triage:** No numerical failures. Golden drift was additive output keys from PHYS-006 schema echo (`P_cd_*_max_MW`, `cd_mix_*`); resolved by intentional regen.

---

## 3. Fixes applied (v417)

See `PATCH_NOTES_v417.md`.

**Safe fixes during development:**

- Certification API alignment (`out=`, `evaluate_*`, v352 UQ stub).
- Golden regen for disabled-overlay key echo (no physics scalar drift in enabled baselines).

---

## 4. Reviewer audit (summary)

| Area | Finding | Risk |
|------|---------|------|
| L0 choke point | Overlays run before v402; no iteration inside truth | Low |
| PHYS-002 | τE scaling only when `profile_proxy_v397_enabled` | Low — gated |
| Registry | JSON is additive; legacy pipelines preserved in `unified.py` | Low |
| PHYS-005 | Reuses existing tritium authority outputs; registry caps only | Low |
| Determinism | Certification digests stable; cache keys unchanged | Low |

**No blockers.**

---

## 5. Validation

| Gate | Result |
|------|--------|
| Full pytest (176) | **PASS** |
| Verification | **PASS** |
| Golden | **PASS** (regen documented) |

**Verdict:** **approved**

---

## 6. PROCESS roadmap (ranked, next cycle)

| Rank | Feature | L0? | Impact |
|------|---------|-----|--------|
| 1 | Registry → constraint code-gen (PROPOSAL-026) | no | H |
| 2 | Constraint pipeline diff UI dossier (PROPOSAL-027) | no | H |
| 3 | NO-SOLUTION mechanism atlas (PROPOSAL-028) | no | H |
| 4 | Complete `ui/decks/` extraction from `app.py` | no | M |
| 5 | Mirage-safe Pareto export lanes (v406 hardening) | no | M |
| 6 | Transport spread gate on all scan kits | no | M |
| 7 | SHA-256 reviewer pack automation | no | M |
| 8 | Fusion performance tier ledger | no | M |
| 9 | Extopt certified-solve firewall hardening | no | M |
| 10 | Overlay toggle dashboard → live `PointInputs` writes | no | M |

---

## 7. UI improvement plan — next sprint

1. Constraint pipeline diff panel (registry vs legacy governance vs ledger side-by-side).
2. Extract remaining deck bodies from `app.py` into `ui/decks/*.py`.
3. Wire v409/v408/v405 overlay toggles in overlay dashboard.
4. Surface `tau_e_profile_factor_v397` in profile authority panel when PHYS-002 active.
5. Mobile-safe verdict strip layout.

---

## 8. Physics / model recommendations (proposals only)

| ID | Recommendation | L0? |
|----|----------------|-----|
| PHYS-003 | Expose v402 reference thresholds in schema/UI | no |
| PHYS-007 | Peaking factor sensitivity envelope on H98 | no |
| PHYS-008 | Wire `phase1_models` H-mode into v396 envelope | no |
| PHYS-009 | ELM duty-cycle coupling to availability ledger | no |
| PHYS-010 | Tritium tight-closure default-on governance preset | no |

**No further L0 changes proposed this cycle** beyond the approved PHYS-002 already merged.

---

## 9. GitHub publish

- **Branch:** `shams/studio-v417-20260703`
- **Merge:** into `main` after validation
