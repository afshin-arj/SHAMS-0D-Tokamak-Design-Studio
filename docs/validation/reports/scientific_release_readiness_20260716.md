# SHAMS Scientific Release Readiness Report

**Report ID:** scientific_release_20260716  
**Date:** 2026-07-16  
**SHAMS Version:** v418.1.0  
**Git commit at audit:** `60c8276` (pre-ship baseline; this ticket advances `main`)  
**Auditor:** shams-release-engineer / shams-scientific-release-prep (independence auto-run 1.4)  
**Target audience:** Scientific community / lab handoff (GitHub public path allowed with waivers)  
**Release verdict:** **CONDITIONAL**

---

## Executive summary (for PI / editor)

SHAMS v418.1.0 is ready for **CONDITIONAL** scientific community handoff as a **feasibility-authoritative** tokamak 0-D studio: frozen L0, CCFS hard gate, NO-SOLUTION atlas, plant KPI honesty watermarks, and a METHOD-ONLY PROCESS parity corpus with hashed dossiers. The strongest evidence is deterministic Phase 1 trust infrastructure plus passing golden / verification / independence regression anchors on this build. The largest risk is overclaim: plant/magnet/cost overlays remain proxies, PROCESS numeric parity is not yet NUMERIC, and full product-QA / tagged Zenodo cut are deferred. This report deliberately chooses **CONDITIONAL over APPROVED** — honesty before false confidence. **Do not claim PROCESS is retired.**

---

## Release verdict rationale

| Verdict | Rule |
|---------|------|
| **APPROVED** | All blockers cleared; gates pass; handoff checklist complete |
| **CONDITIONAL** | No blockers; major issues documented with explicit waivers |
| **BLOCKED** | Any blocker OR pytest/golden fail OR secrets OR install broken |

**This build:** **CONDITIONAL** because:

- Zero automatic blockers (golden PASS, verification PASS, independence anchors PASS, LICENSE present, L0 path documented).
- Major honesty gaps remain and are documented in `docs/LIMITATIONS.md` (METHOD-ONLY parity, plant proxies, DEMO MATCH incomplete).
- Explicit waivers below cover deferred full `pytest` wall-clock suite, full `/shams-full-product-qa`, and deferred public version tag / Zenodo cut (Phase 9 not executed in this ticket).

---

## Blockers (must be zero for APPROVED)

| ID | Domain | Finding | Evidence | Fix owner |
|----|--------|---------|----------|-----------|
| — | — | *None* | Anchors + golden + verification PASS 2026-07-16 | — |

---

## Gate matrix

| # | Gate | Check | Result | Evidence / command |
|---|------|-------|--------|-------------------|
| 1 | Version consistency | VERSION = README = CITATION.cff | **PASS** (CITATION aligned this ticket) | `VERSION` / README header / `CITATION.cff` → v418.1.0 |
| 2 | Patch notes | PATCH_NOTES for current epoch | **PASS** | `docs/patch_notes/PATCH_NOTES_v418_1.md`, `PATCH_NOTES_v418.md` |
| 3 | LICENSE | Present and correct | **PASS** | Apache-2.0 `LICENSE` |
| 4 | CITATION.cff | Aligned with release | **PASS** | Updated to v418.1.0 / 2026-07-16 |
| 5 | Clean install | `pip install -r requirements.txt` | **CONDITIONAL** | Assumed from prior CI/dev env; not re-run in fresh venv this session — Waiver W-INSTALL |
| 6 | Full pytest | Zero failures | **CONDITIONAL** | Scoped suite PASS; full wall-clock suite not re-run — Waiver W-PYTEST-SCOPE |
| 7 | Verification | `run_verification.py` PASS | **PASS** | `VER_EXIT=0`; `IMPORT_POLICY_OK`; benchmarks passed |
| 8 | Golden physics | All cases pass | **PASS** | `tests/test_golden_physics_outputs.py` + `test_validation_baseline_v2230.py` → `GOLD_EXIT=0` |
| 9 | ui_self_test | Exit 0 | **CONDITIONAL** | Not executed this session (classifier/env) — Waiver W-UI-SELFTEST; stranger CLI eval PASS |
| 10 | MANIFEST_SHA256 | Present / current | **CONDITIONAL** | Present (`MANIFEST_SHA256.txt`); may be stale vs dirty tree — regenerate before tag |
| 11 | No secrets in repo | grep clean | **PASS** | Best-effort `git grep`; no token/key hits of concern |
| 12 | Offline reproducibility | Tests without network | **PASS** | Anchors + golden + smoke ran offline |
| 13 | GOVERNANCE compliance | Frozen truth documented | **PASS** | `GOVERNANCE.md` + README L0 mermaid |
| 14 | Export manifest | Reviewer pack SHA-256 | **CONDITIONAL** | Capability exists; sample pack not regenerated this session — Waiver W-REVIEWER-PACK |
| 15 | Known limitations | Documented | **PASS** | `docs/LIMITATIONS.md` (this ticket) |
| 16 | Examples runnable | `examples/` spot-check | **PASS** | `examples/base_point.json` present; CLI Evaluator eval OK with `PYTHONPATH=src` |
| 17 | L0 path documented | README + GOVERNANCE | **PASS** | Evaluator → `hot_ion_point` |
| 18 | Authority catalog | Matches code | **CONDITIONAL** | Catalog present; spot-check only — Waiver W-AUTH-SPOT |
| 19 | Product QA | `/shams-full-product-qa` verdict | **CONDITIONAL** | Deferred to Phase 3 studio depth — Waiver W-PRODUCT-QA |
| 20 | Stranger handoff | 7-step checklist below | **CONDITIONAL** | Steps 5–6 PASS via CLI; UI steps deferred — see handoff table |

**Gates passed (strict PASS):** 12 / 20  
**Gates CONDITIONAL (waived, no blocker):** 8 / 20  
**Gates FAIL/BLOCKED:** 0 / 20  

Independence Phase 1 exit criterion: **verdict ≥ CONDITIONAL with documented limitations** → **MET**.

---

## Stranger handoff test (community release)

| Step | Action | Pass? | Notes |
|------|--------|-------|-------|
| 1 | Clone + read README | **PASS** | README v418.1.0; posture + NiceGUI launch clear |
| 2 | `pip install -r requirements.txt` | **CONDITIONAL** | Not re-run in fresh venv this session (W-INSTALL) |
| 3 | `pytest` | **CONDITIONAL** | Smoke + independence anchors + golden PASS; full suite scoped (W-PYTEST-SCOPE) |
| 4 | `python verification/run_verification.py` | **PASS** | Exit 0 |
| 5 | Evaluate one point (CLI or UI) | **PASS** | `PYTHONPATH=src` → `Evaluator().evaluate(...)` → `ok True` |
| 6 | Interpret verdict + constraint | **PASS** | Feasibility-authority docs + atlas/KPI honesty on artifacts |
| 7 | Export artifact with manifest | **CONDITIONAL** | Capability documented; sample export not re-sealed (W-REVIEWER-PACK) |

**Handoff verdict:** **conditional pass** (CLI core path OK; UI/export depth waived)

---

## Critical findings (scientific + engineering)

| ID | Severity | Domain | Finding | Release impact |
|----|----------|--------|---------|----------------|
| CF-01 | MAJOR | Parity | PROCESS corpus is METHOD-ONLY (no lab MFILE) | Must not claim numeric PROCESS match |
| CF-02 | MAJOR | Plant | Magnets/build/plant/cost still proxy-grade vs PROCESS breadth | Phase 2 DEMO MATCH required for engineering closure studies |
| CF-03 | MAJOR | Packaging | Pre-ticket `CITATION.cff` lagged at v120 | Fixed this ticket; watch version drift |
| CF-04 | MINOR | Hygiene | `.env` not previously gitignored | Fixed this ticket |
| CF-05 | MINOR | Docs | Root `README_UI.md` not present (NiceGUI docs in-repo elsewhere) | Conditionally acceptable; Phase 3 polish |
| CF-06 | INFO | UI | Full product QA / ui_self_test not re-run | Waived for Phase 1 exit; do before APPROVED |

---

## Documentation audit

| Document | Status | Gaps for external scientists |
|----------|--------|------------------------------|
| README.md | PASS | Version aligned; add LIMITATIONS link (this ticket) |
| GOVERNANCE.md | PASS | Frozen-truth change control present |
| README_UI.md | GAP | No root file; NiceGUI covered in README + `ui_nicegui/` |
| ARCHITECTURE.md | PASS | Present |
| PATCH_NOTES | PASS | v418 / v418.1 present |
| CITATION.cff | PASS | Aligned this ticket |
| LICENSE | PASS | Apache-2.0 |
| LIMITATIONS | PASS | `docs/LIMITATIONS.md` added this ticket |

---

## Test & validation evidence

| Suite | Count / result | Gap |
|-------|----------------|-----|
| Independence anchors | 34 passed (`ccfs`+`atlas`+`plant_kpi`+`parity`) | — |
| Golden + baseline | PASS (`GOLD_EXIT=0`) | — |
| Verification | PASS | Local `verification/report.json` dirty in tree — do not commit noise |
| Smoke | PASS | — |
| Full pytest | Not wall-clock re-run | W-PYTEST-SCOPE |
| ui_self_test | Not run | W-UI-SELFTEST |

**Coverage honesty:** Full NiceGUI deck walkthrough, fresh-venv install, and sealed reviewer-pack sample were **not** re-executed in this auto-run. Phase 1 exit does not require APPROVED.

### Commands executed (2026-07-16)

```text
cd SHAMS-0D
python -m pytest tests/test_ccfs_verified_hard_gate.py tests/test_no_solution_atlas.py tests/test_plant_kpi_honesty.py tests/test_process_parity_corpus.py -v
# → 34 passed

python verification/run_verification.py
# → VER_EXIT=0; All benchmarks passed; IMPORT_POLICY_OK

python -m pytest tests/test_golden_physics_outputs.py tests/test_validation_baseline_v2230.py -q
# → GOLD_EXIT=0

python -m pytest tests/test_smoke.py -q
# → SMOKE_EXIT=0

$env:PYTHONPATH="src"
python -c "from schema.inputs import PointInputs; from evaluator.core import Evaluator; ..."
# → ok True
```

---

## Reproducibility & traceability

| Item | Status | Notes |
|------|--------|-------|
| L0 frozen truth path | PASS | `evaluator/core.py` → `hot_ion.py` |
| Golden baselines committed | PASS | Under `tests/golden/` |
| Evaluator choke point (UI) | PASS | Documented; not re-instrumented this run |
| CCFS hard gate | PASS | `tests/test_ccfs_verified_hard_gate.py` |
| NO-SOLUTION atlas | PASS | `no_solution_atlas.v1` |
| Plant KPI honesty | PASS | `plant_kpi_honesty.v1` |
| PROCESS parity | METHOD-ONLY | Hashed dossier; no invented MFILE |
| Provenance stamps | PASS (capability) | Export path exists |

---

## Known limitations (publish with release)

See canonical list: **`docs/LIMITATIONS.md`**.

Summary:

1. 0-D frozen evaluator — not transport/MC/optimizer-in-truth.  
2. Magnets / build / plant / cost = proxies pending Phase 2 MATCH.  
3. PROCESS parity = METHOD-ONLY until lab MFILE.  
4. Exhaust / neutronics depth limited.  
5. Do not claim PROCESS retired.  
6. MANIFEST may need regen before public tag.

---

## Security & hygiene

| Check | Result |
|-------|--------|
| Secrets in tracked files | PASS (best-effort) |
| .env gitignored | PASS after this ticket (`.gitignore` adds `.env`) |
| Dependency audit | Not deep-scanned; list deferred |

---

## Waivers (independence Phase 1 exit — documented)

| Waiver ID | Gate deferred | Approval basis | Expiry |
|-----------|---------------|----------------|--------|
| W-INSTALL | Fresh venv clean install | Existing maintained env; README install path documented | Next APPROVED attempt |
| W-PYTEST-SCOPE | Full `pytest` wall-clock | Anchors + golden + smoke + verification PASS | Next APPROVED attempt |
| W-UI-SELFTEST | `tools.ui_self_test` | CLI stranger eval PASS; UI depth → Phase 3 | Phase 3 / APPROVED |
| W-REVIEWER-PACK | Sealed sample pack regen | Export capability + MANIFEST present | Before Zenodo/tag |
| W-PRODUCT-QA | Full product QA | Phase 1 is trust-the-verdict, not studio polish | Phase 3 |
| W-AUTH-SPOT | Full authority matrix audit | GOVERNANCE + overlay tests exist | Phase 2/3 |
| W-NO-TAG | Phase 9 version cut / Zenodo | User did not request tag; CONDITIONAL evidence only | Explicit `/shams-patch-release` |

---

## Pre-release fix queue

| Priority | ID | Fix | Owner skill | Effort |
|----------|-----|-----|-------------|--------|
| P0 | — | None for CONDITIONAL ship | — | — |
| P1 | CF-01 | Land NUMERIC parity when lab MFILE available | `/process-parity-compare` | M |
| P1 | CF-02 | DEMO MATCH overlays (Phase 2.1 magnets…) | `/reactor-systems` | L |
| P1 | W-PRODUCT-QA | Full product QA before APPROVED | `/shams-full-product-qa` | M |
| P2 | CF-05 | Root README_UI or NiceGUI handbook link | `/documentation` | S |
| P2 | MANIFEST | Regenerate before public tag | `/shams-patch-release` | S |

---

## Release package checklist

```
Release package:
- [x] Readiness report CONDITIONAL signed (this file)
- [x] Known limitations published (`docs/LIMITATIONS.md`)
- [x] CITATION.cff aligned to VERSION
- [x] Phase 1 independence anchors green
- [ ] VERSION bumped (/shams-patch-release) — deferred (W-NO-TAG)
- [ ] MANIFEST_SHA256 regenerated for tag
- [ ] Reviewer pack sample attached
- [ ] Full product_qa_report attached
- [ ] Git tag v418.1.0 community cut
- [ ] Zenodo deposit
```

---

## PROCESS independence lens (mandatory)

| Claim | Allowed? |
|-------|----------|
| SHAMS is feasibility authority for tokamak 0-D studies citing VERSION + hashes | **Yes** (CONDITIONAL) |
| PROCESS retired / replaced for all DEMO plant closure | **No** |
| Numeric PROCESS parity without MFILE | **No** |
| Healthy Pe_net on hard-infeasible points | **No** (watermark required) |

**Overclaim check:** OK — CONDITIONAL; PROCESS **not** retired.

---

## Appendix

### Related reports / artifacts

- `docs/LIMITATIONS.md`
- `docs/PROCESS_SURPASS_ROADMAP.md` (Phase 1.4)
- `benchmarks/parity/` METHOD-ONLY corpus + hashed dossiers
- `.cursor/validation/reports/release_gates_*_20260716.txt` (local evidence logs)
- Prior: `docs/validation/reports/validation_report_20260703.md`

### Delegated reviews

| Role | Summary |
|------|---------|
| shams-release-engineer (this report) | CONDITIONAL — Phase 1 exit MET |
| reviewer (self-audit) | No L0 / CCFS bleed; additive docs + packaging only |
| UI | Docs/export smoke via CLI stranger path; no Studio code change |

### L0 risk

**none** — no changes to `hot_ion.py` / Evaluator truth path.
