# SHAMS Release & Archival Checklist (Zenodo / DOI / citation)

**Independence Phase 3.2 — Zenodo / CITATION / software-paper pitch.**
**Related:** `CITATION.cff`, `.zenodo.json`, `docs/LIMITATIONS.md`, `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`, `docs/validation/reports/scientific_release_readiness_20260716.md`, `GOVERNANCE.md`, `docs/SOFTWARE_PAPER_PITCH.md`.

This document defines how a SHAMS release is cut, archived on Zenodo, assigned a DOI, and cited — and what must happen before the release verdict can flip **CONDITIONAL → APPROVED**. It does **not** claim APPROVED status now, does **not** claim PROCESS retirement, and does **not** invent PROCESS MFILE numbers.

---

## 1. Current release posture (honest)

- **Verdict at v418.1.0:** **CONDITIONAL** — see `docs/validation/reports/scientific_release_readiness_20260716.md` (12/20 strict PASS, 8/20 waived, 0 blockers).
- **No public version tag and no Zenodo deposit have been cut yet** (waiver W-NO-TAG). `.zenodo.json` and `CITATION.cff` are prepared metadata, not evidence of a minted DOI.
- PROCESS numeric parity remains **METHOD-ONLY**; SHAMS is a feasibility authority, not a PROCESS clone.

---

## 2. The APPROVED-release path (gates that flip CONDITIONAL → APPROVED)

APPROVED requires **all** Phase 1.4 waivers to be cleared with fresh evidence, on a clean tree, in one audited pass (`/shams-release-engineer` + `/shams-scientific-release-prep`). Documented gates:

| Gate | Waiver cleared | Evidence required |
|------|----------------|-------------------|
| G1 Fresh-venv install | W-INSTALL | `pip install -r requirements.txt` in a new venv; import + smoke pass |
| G2 Full pytest wall-clock | W-PYTEST-SCOPE | `python -m pytest` zero failures (or documented pre-existing exceptions triaged to zero) |
| G3 UI self-test | W-UI-SELFTEST | `tools.ui_self_test` exit 0 + NiceGUI deck walkthrough |
| G4 Sealed reviewer pack | W-REVIEWER-PACK | Sample export with regenerated `MANIFEST_SHA256.txt`; hashes verified |
| G5 Full product QA | W-PRODUCT-QA | `/shams-full-product-qa` report with no P0/P1 blockers |
| G6 Authority matrix audit | W-AUTH-SPOT | Overlay catalog ↔ code audit (declared ON/OFF defaults, provenance keys) |
| G7 Version cut | W-NO-TAG | `/shams-patch-release`: VERSION bump, patch notes, tag prepared |
| G8 Readiness report | — | New `scientific_release_readiness_<date>.md` with verdict **APPROVED**, zero blockers, zero unexpired waivers |

Additional honesty invariants that must hold at APPROVED (they are release-gate anchors already):

- `docs/LIMITATIONS.md` ships with the release and stays truthful (proxies, METHOD-ONLY parity).
- No "PROCESS retired" claim anywhere without a scoped `process_retirement_report`.
- `CITATION.cff` `version:` equals `VERSION` equals README header.

**Until all of G1–G8 pass, the verdict stays CONDITIONAL. Do not tag, do not deposit.**

---

## 3. Cutting a tagged release (when the APPROVED gates pass)

1. Clean tree on `main`; full test + verification evidence archived.
2. Run `/shams-patch-release`: bump `VERSION`, write `docs/patch_notes/PATCH_NOTES_<ver>.md`, align `CITATION.cff` (`version:` + `date-released:`) and `.zenodo.json` (`version` + `publication_date`).
3. Regenerate `MANIFEST_SHA256.txt` on the release tree.
4. Commit, then tag: `git tag -a <ver> -m "SHAMS <ver> community release"` and `git push origin <ver>` (never force-push).
5. Create the GitHub Release from the tag; attach the readiness report and a sealed reviewer-pack sample.

## 4. Zenodo deposit and DOI

1. Preferred path: enable the **GitHub–Zenodo integration** for the repository once; every subsequent GitHub Release is archived automatically and receives a version DOI (plus a concept DOI covering all versions). Zenodo reads `.zenodo.json` for metadata.
2. Manual fallback: upload the tagged source archive to Zenodo, paste metadata from `.zenodo.json`, and publish to mint the DOI.
3. After the first deposit: record the concept DOI and version DOI in `CITATION.cff` (`doi:` field), README citation section, and the next patch notes.
4. Verify the Zenodo record lists the license (Apache-2.0), repository URL, and the honest description (proxies, METHOD-ONLY parity, no retirement claim).

## 5. How to cite SHAMS (community rule)

Every SHAMS-based feasibility study must cite:

1. **Software:** `CITATION.cff` metadata (title, authors, version, DOI once minted).
2. **Exact truth version:** the `VERSION` string of the build that produced the results (e.g. `v418.1.0`).
3. **Artifacts:** the SHA-256 hashes of the exported run artifacts / reviewer pack (`MANIFEST_SHA256.txt` or the per-artifact manifest), so any reviewer can re-evaluate the same inputs against the same frozen L0 and get the same outputs.
4. **For PROCESS comparisons:** attach a parity dossier (METHOD-ONLY or NUMERIC) from `benchmarks/parity/` and declare assumptions — never invent MFILE numbers.

---

## 6. Anti-overclaim rules (apply to every release)

- Never present a CONDITIONAL build as APPROVED.
- Never claim PROCESS is retired or replaced for DEMO plant closure without a scoped `process_retirement_report` and parity dossiers.
- Never mint a DOI on a tree whose golden / verification / release-gate anchors are failing.
- NO-SOLUTION results are valid science; do not smooth them away for a release narrative.
