# SHAMS ↔ PROCESS Surpass Roadmap

Living campaign document.

| Invoke | Role |
|--------|------|
| **`/shams-process-independence`** | **Super-agent** — Phase 0–4 independence; **auto-run** ticket → deep UI/core → push `main` → next step |
| `/shams-surpass-process` | Sprint gap ranking |
| `/process-specialist` | Upstream PROCESS intelligence |
| `/process-capability-audit` | Domain inventory |
| `/process-parity-compare` | Numeric / METHOD-ONLY dossiers |

**Upstream:** [ukaea/PROCESS](https://github.com/ukaea/PROCESS) · [docs](https://ukaea.github.io/PROCESS/)  
**SHAMS version at last refresh:** see `VERSION`  
**Last analytical refresh:** 2026-07-17

## Independence phases (campaign)

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Stance & firewall | **Mostly done** | CCFS hard gate on `main`; agents/skills updated |
| 1 Trust the verdict | **DONE** 2026-07-16 | Tickets 1.1–1.4 complete (atlas, plant KPI honesty, METHOD-ONLY parity, scientific release gate **CONDITIONAL**) |
| 2 DEMO MATCH | **DONE** 2026-07-17 | 2.1–2.3 DONE 2026-07-16 (v410 magnets; v412 radial/machine-build; v419 plant Sankey ledger); 2.4 DONE 2026-07-17 (**v420** availability → OPEX/LCOE coupling); 2.5 DONE 2026-07-17 (**v421** bottom-up modular costing — not 1990 Generomak) |
| 3 Community default | **DONE** 2026-07-17 | 3.1 migration guide; 3.2 Zenodo/CITATION/paper pitch; 3.3 champion cases; 3.4 Studio default entry — all **DONE** 2026-07-17 |
| 4 Independence | **Engineering complete; exit open** | 4.1–4.3 **DONE** 2026-07-17 — citation unit, scoped retirement, parity contribution + exit evidence shipped; full Phase-4 *exit* still open (community adoption + APPROVED DOI = **EXTERNAL**) |

## Stance (do not blur)

| | PROCESS | SHAMS |
|--|---------|-------|
| Core question | What design optimizes a FoM under solvable constraints? | Which designs are admissible, how robust, and why others fail? |
| Numerics | VMCON / fsolve inside the model graph | Frozen L0 evaluator; solvers propose inputs only |
| Failure | Avoid / VaryRun | NO-SOLUTION + mechanism attribution |
| Credibility | DEMO / STEP / Zenodo / decades of models | Determinism, governance, reviewer packs, modern authorities |

SHAMS does **not** win by reimplementing PROCESS megamodules first. SHAMS wins by keeping L0 frozen and selectively importing PROCESS-class **coverage** as versioned overlays.

---

## PROCESS architecture snapshot (upstream)

```
IN.DAT → parse/defaults → DataStructure (mutable)
       → ioptimz=-2: fsolve equalities
       → ioptimz=1:  VMCON FoM + eq/ineq
       → Caller models (geometry→physics→eng→power→cost)
       → idempotence re-evals → OUT.DAT / MFILE.DAT
```

**Major model areas:** plasma physics (geometry, profiles, fusion, beta, density limit, radiation, current, HCD, confinement, pulsed), machine build, TF/PF/CS + superconductors, FW/blanket/shield/divertor, cryostat/vacuum, structure, plant power, buildings, availability, water use, costs (1990 COE / 2015 capital), ST / stellarator / IFE branches.

**Strengths:** plant breadth, constraint catalog, institutional papers, MFILE tooling, magnet depth.  
**Debts:** global mutable state, FD-SQP fragility, integer switches, aged costs, thin exhaust, no frozen-truth choke point, weak interactive studio.

---

## SHAMS maturity matrix (2026-07-16)

| Area | Maturity | Notes |
|------|----------|-------|
| L0 evaluator / hot_ion | **Strong** | Same inputs → same outputs |
| Confinement / Q / burn | **Strong** | Multi-scaling; phase1 models |
| Constraints ontology | **Strong** | Hard / diagnostic / ignored |
| Systems Mode / extopt | **Strong** | Propose-only contract |
| UI (Streamlit / NiceGUI) | **Partial→Strong** | Verdict-first studio (PROCESS has CLI) |
| Magnets / radial build | **Partial→Stronger** | v400 ON + **v410** TF/PF/CS SC + **v412** machine-build radial closure (proxy; OFF default) |
| Plant ledger / power | **Partial→Stronger** | v408 CD-mix + **v419** Sankey-grade source→sink ledger + **v420** availability→OPEX/LCOE chain (proxy; OFF default; KPI honesty watermark) |
| Divertor / exhaust | **Proxy** | PROCESS also thin — BEAT target |
| Neutronics / TBR | **Proxy** | v401/v407/v408 scaffolding |
| Economics | **Proxy→Stronger** | **v421** bottom-up modular CAPEX account ledger (transparent rates; OFF default); still not a bankable cost model — do not clone 1990 Generomak as truth |
| Neutrals / edge | **Missing** | |
| PROCESS numeric parity corpus | **METHOD-ONLY** | `process.parity_cases.v2` + hashed delta dossier; NUMERIC when lab MFILE lands |
| Stellarator / IFE | **Ignore (default)** | Breadth tax |

---

## Strategy legend

- **BEAT** — SHAMS unique scientific or UX advantage; prioritize.
- **MATCH-as-overlay** — Need PROCESS-class coverage for credibility; never into L0.
- **IGNORE** — Out of mission or low ROI vs frozen-truth focus.

---

## Ranked campaign backlog

Derived from audit `docs/validation/reports/audit_report_20260703.md` + 2026-07-16 upstream inventory + `/reviewer` re-rank (credibility-first) + `/reactor-systems` MATCH set.

| Rank | Item | Strategy | L0? | Effort | Impact | Next skill / agent |
|------|------|----------|-----|--------|--------|--------------------|
| 1 | Extopt CCFS certified-solve firewall | BEAT | no | M | H | `/pareto-frontier-check` |
| 2 | NO-SOLUTION mechanism atlas | BEAT | no | M | H | `/shams-feature-development` |
| 3 | ~~PROCESS parity corpus + delta dossiers~~ **DONE** 2026-07-16 (METHOD-ONLY honesty + hashed dossier) | BEAT | no | M | H | `/process-parity-compare` |
| 4 | ~~Plant power ledger honesty (gate Pe_net on hard feasibility) + Sankey audit~~ **DONE** 2026-07-16 (`plant_kpi_honesty.v1`) + **Sankey-grade ledger DONE** 2026-07-16 (`plant_sankey_ledger_authority_v419`) | MATCH | no | M | H | `/reactor-systems` |
| 5 | Exhaust / divertor authority depth | BEAT | no | M | H | `/reactor-systems` |
| 6 | ~~Magnet / SC / PF–CS overlay depth (post-v400)~~ **DONE** 2026-07-16 (`magnet_sc_system_authority_v410`) | MATCH | no | L | H | `/reactor-systems` |
| 7 | ~~Radial-build closure narrative~~ **DONE** 2026-07-16 (`machine_build_authority_v412`) | MATCH | no | M | M | `/architect` |
| 8 | Native UQ / mirage-safe robust lanes | BEAT | no | L | H | `/pareto-frontier-check` |
| 9 | ~~Availability → OPEX / LCOE coupling~~ **DONE** 2026-07-17 (`availability_opex_lcoe_authority_v420`) | MATCH | no | M | M | `/reactor-systems` |
| 10 | ~~Bottom-up modular costing (not 1990 Generomak)~~ **DONE** 2026-07-17 (`bottom_up_costing_authority_v421`) | MATCH | no | L | M | `/shams-feature-development` |
| 11 | SHA-256 reviewer pack + nuclear provenance | BEAT | no | S | H | `/reviewer-pack-export` |
| 12 | Fusion performance tier ledger | BEAT | no | M | H | `/fusion-performance` |
| 13 | Transport envelope gate on scans (v396) | BEAT | no | S | M | `/transport-specialist` |
| 14 | Policy-tier constraint explorer UI | BEAT | no | M | M | `/ui-specialist` |
| 15 | v402 dominance dashboard polish (v411 host landed) | BEAT | no* | S | M | `/authority-overlay-author` |
| 16 | ST centerpost path (STEP-aligned, selective) | MATCH | no | L | M | `/process-capability-audit` |
| 17 | Stellarator / IFE | IGNORE | — | — | — | unless requested |

\* v402 dominance: pipeline import in v411; remaining work is UI/E2E polish, not L0 unblock.

### Top 3 next week

1. ~~Harden CCFS (`src/extopt/certified_solve.py` + tests: VERIFIED ≠ claims when hard fail)~~ **DONE** (Evaluator + governance hard gate; `tests/test_ccfs_verified_hard_gate.py`)
2. ~~Ship NO-SOLUTION atlas on every infeasible artifact (`src/diagnostics/no_solution_atlas.py`)~~ **DONE** 2026-07-16 — stamped on hard-infeasible `build_run_artifact`, CCFS REJECTED rows, campaign error artifacts, PD/CR export bundles (`no_solution_atlas.v1`)
3. ~~Fill `benchmarks/parity/process_reference_cases.json` (≥1 real PROCESS ref + hashed delta dossier; no invented MFILE)~~ **DONE** 2026-07-16 — METHOD-ONLY corpus (`process.parity_cases.v2`), hashed dossier `benchmarks/parity/dossiers/method_only_hts_compact_001_delta_dossier.json`, honesty gate in `src/parity_harness/process_corpus.py` (`tests/test_process_parity_corpus.py`). NUMERIC upgrade path documented; no invented MFILE numbers.
4. ~~Plant KPI honesty — gate healthy `Pe_net` / COE on hard feasibility watermark~~ **DONE** 2026-07-16 — `plant_kpi_honesty.v1` on every run artifact; Suite/Systems Mode watermark Pe_net/COE/LCOE when hard-infeasible (`tests/test_plant_kpi_honesty.py`)
5. ~~Scientific release gate (Phase 1.4)~~ **DONE** 2026-07-16 — verdict **CONDITIONAL** (`docs/validation/reports/scientific_release_readiness_20260716.md`); limitations `docs/LIMITATIONS.md`; CITATION.cff ↔ VERSION aligned; lock tests `tests/test_scientific_release_gate.py`. Phase 1 exit MET. No PROCESS-retired claim; no VERSION tag/Zenodo cut (deferred to APPROVED path).
6. ~~**Next (Phase 2.1):** TF/PF/CS SC depth beyond v400~~ **DONE** 2026-07-16 — `magnet_sc_system_authority_v410` (MATCH-as-overlay; OFF by default; PROXY-labeled TF/PF/CS family ledgers + system margin; optional hard/diagnostic caps; UI watermark on Point Designer / Suite). L0 numeric truth unchanged when flag OFF (empty patch). No invented PROCESS MFILE numbers.
7. ~~**Next (Phase 2.2):** Radial / machine-build closure~~ **DONE** 2026-07-16 — `machine_build_authority_v412` (MATCH-as-overlay; OFF by default; PROXY layer-stack ledger, clearances/gaps, inboard closure + outboard envelope narrative; optional caps; UI on PD/Suite/authority dashboard). L0 unchanged when flag OFF. No invented PROCESS MFILE numbers.
8. ~~**Next (Phase 2.3):** Plant Sankey-grade ledger (extend v408)~~ **DONE** 2026-07-16 — `plant_sankey_ledger_authority_v419` (MATCH-as-overlay; OFF by default; PROXY source→sink flows, recirc breakdown, conservation checks; UI Sankey/flow-table with plant_kpi_honesty watermark). L0 unchanged when flag OFF. No invented PROCESS MFILE numbers.
9. ~~**Next (Phase 2.4):** Availability → OPEX/LCOE coupling~~ **DONE** 2026-07-17 — `availability_opex_lcoe_authority_v420` (MATCH-as-overlay; OFF by default; one availability chain v368→v359→v391→availability_model→input with provenance feeds hours → annual energy → OPEX → LCOE on the same basis; centralized OPEX formulas in `src/economics/opex_coupling.py`; LCOE decomposition + bookkeeping/cross-ledger consistency checks; `avail_v420_LCOE_USD_per_MWh` in plant_kpi_honesty.v1 aliases; optional caps A_min/LCOE_max/OPEX_max; UI chain table on PD/Suite/dashboard). L0 unchanged when flag OFF. No invented PROCESS MFILE numbers; not 1990 Generomak.
10. ~~**Next (Phase 2.5):** Bottom-up modular costing authority (not 1990 Generomak)~~ **DONE** 2026-07-17 — `bottom_up_costing_authority_v421` (MATCH-as-overlay; OFF by default; 13-row direct/indirect CAPEX account ledger with explicit drivers, units, and transparent in-repo unit rates; bookkeeping identity checks + informational cross-checks vs legacy/v356/v388/v420 CAPEX bases; LCOE restated only on the v420 availability chain basis and registered in plant_kpi_honesty.v1 aliases; optional caps with version-tag-free UI names). L0 unchanged when flag OFF. Not 1990 Generomak; no invented PROCESS MFILE numbers. **Phase 2 (DEMO MATCH) complete.**
11. ~~**Next (Phase 3.1):** PROCESS → SHAMS migration guide~~ **DONE** 2026-07-17 — `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` (IN.DAT→Case/`PointInputs`, MFILE→artifacts, constraint/policy mapping, VERSION+SHA-256 citation, CCFS propose-only, METHOD-ONLY honesty). Crosswalk/README/LIMITATIONS link in; Control Room Docs Library + Launchpad entry. Lock tests: `tests/test_process_migration_guide.py`. No invented MFILE numbers; no PROCESS-retired claim.
12. ~~**Next (Phase 3.2):** Zenodo / CITATION / software paper pitch — clear APPROVED release path~~ **DONE** 2026-07-17 — `.zenodo.json` archival metadata aligned to `VERSION`; `CITATION.cff` packaging fields verified (license, repository URL; ORCID left as commented note — never invented); `docs/RELEASE_ARCHIVAL_CHECKLIST.md` (tag → Zenodo deposit → DOI → cite VERSION + artifact SHA-256; documented CONDITIONAL→APPROVED gates G1–G8 clearing all Phase 1.4 waivers — APPROVED **not** claimed); `docs/SOFTWARE_PAPER_PITCH.md` (JOSS-style skeleton: statement of need, functionality, honest comparison stance — PROCESS optimizes, SHAMS certifies feasibility; METHOD-ONLY parity and CONDITIONAL status stated). Lock tests: `tests/test_release_archival_packaging.py`. No DOI minted; no PROCESS-retired claim.
13. ~~**Next (Phase 3.3):** Champion cases — reproducible SHAMS-only feasibility studies~~ **DONE** 2026-07-17 — `docs/CHAMPION_CASES.md`; cases `benchmarks/champions/cases.json`; runner `benchmarks/champions/run_champions.py`; API `src/studies/champion_cases.py` (Design Intent hard set; deterministic citation SHA-256; NO-SOLUTION atlas on infeasible). Lock tests: `tests/test_champion_cases.py`. Docs Library + Launchpad entry. No invented MFILE numbers; no PROCESS-retired claim.
14. ~~**Next (Phase 3.4):** Studio as default entry — NiceGUI/Streamlit verdict-first UX for systems studies~~ **DONE** 2026-07-17 — verdict-first landing card on the default deck (Point Designer renders "Start a systems study" until first evaluation: what SHAMS answers, NO-SOLUTION as first-class outcome, three-step path to a certified verdict); champion templates (3.3) load as one-click starting points via `ui_nicegui/lib/studio_entry.py` (deterministic PointInputs, propose-only — user still clicks Evaluate); onboarding doc buttons deep-link Control Room Docs Library (migration guide + champion cases); Launchpad champion path now routes to Point Designer; Streamlit parity getting-started block on Point Designer. No version tags in user-facing labels. Lock tests: `tests/test_studio_default_entry.py`. No PROCESS-retired claim. **Phase 3 (Community default) complete.**
15. ~~**Next (Phase 4.1):** Scoped PROCESS retirement evidence report~~ **DONE** 2026-07-17 — `src/reports/process_retirement_report.py` (`shams.process_retirement_report.v1`); artifacts `docs/PROCESS_RETIREMENT_REPORT.md` + `docs/validation/reports/process_retirement_report.json`; cites VERSION + champion citation SHA-256 + parity dossier hashes + DEMO MATCH overlay hashes + CONDITIONAL release gate; 8 SCOPED_COVERED/PROXY domains + 6 explicit NOT_COVERED; honesty gate refuses blanket “PROCESS retired” and METHOD-ONLY→numeric overclaim. Docs Library + Studio entry link (version-tag-free label). Lock tests: `tests/test_process_retirement_report.py`. L0 untouched.
16. ~~**Next (Phase 4.2):** Cite-SHAMS handoff pack~~ **DONE** 2026-07-17 — `src/reports/cite_shams_handoff_pack.py` (`shams.cite_shams_handoff_pack.v1`); one-click/CLI ZIP bundling VERSION, optional git describe, PointInputs, run artifact + SHA-256, evaluation export (reuses `ui.export_bundle`), NO-SOLUTION atlas when infeasible, CITATION.cff-derived `citation.txt`/`citation.bib`, CONDITIONAL `release_gate.json`, `HONESTY.md` (PROCESS import optional; METHOD-ONLY; no blanket retirement). Doc: `docs/CITE_SHAMS_HANDOFF.md`. UI: NiceGUI Point Designer + Control Room Export & Share + Streamlit PD Export Bay; Studio/Docs Library links. Lock tests: `tests/test_cite_shams_handoff_pack.py`. L0 untouched.
17. ~~**Next (Phase 4.3):** Parity contribution process + independence exit evidence~~ **DONE** 2026-07-17 — `src/parity_harness/contribution.py` (`shams.parity_contribution.v1` intake + honesty: NUMERIC only with real KPIs/provenance/license); CLI `contribute`; template `benchmarks/parity/contributions/submission_template.json`; doc `docs/PARITY_CONTRIBUTION.md`. Exit evidence: `src/reports/independence_exit_evidence.py` (`shams.independence_exit_evidence.v1`) → `docs/INDEPENDENCE_EXIT_EVIDENCE.md` + `docs/validation/reports/independence_exit_evidence.json` (shipped gates DONE; release CONDITIONAL; adoption/DOI EXTERNAL; refuses blanket retirement). Docs Library + Studio links (version-tag-free). Lock tests: `tests/test_parity_contribution_and_exit_evidence.py`. L0 untouched. **Phase 4 engineering complete; full exit remains open on EXTERNAL items.**

### Campaign status after 4.3

In-repo PROCESS-independence **engineering** for Phases 0–4 is complete. Remaining for *effective* independence in the wild:

1. **EXTERNAL** — community adoption (new studies cite SHAMS by default)
2. **EXTERNAL** — APPROVED scientific release + Zenodo DOI
3. Optional BEAT/MATCH backlog items (exhaust depth, UQ, etc.) are **not** Phase-4 exit blockers — see ranked backlog above

**Next independence invoke:** no further Phase-4 tickets; use `/shams-process-independence` only to re-verify exit evidence or pick a post-campaign BEAT item (e.g. exhaust / divertor authority) if the user requests continued surpass work.

### Minimum DEMO MATCH overlays (reactor-systems)

1. ~~TF/PF/CS SC depth beyond v400~~ **DONE** (`v410`)
2. ~~Radial / machine-build closure~~ **DONE** (`v412`)
3. ~~Plant Sankey-grade ledger (extend v408)~~ **DONE** (`v419`)
4. ~~Availability → energy/OPEX~~ **DONE** (`v420`)
5. ~~Bottom-up modular costing auth~~ **DONE** (`v421`)

All five minimum DEMO MATCH overlays shipped — Phase 2 complete 2026-07-17.

---

## What SHAMS already beats PROCESS at

1. Deterministic frozen evaluator  
2. Explicit NO-SOLUTION as science  
3. Typed hard/diagnostic/ignored constraints  
4. External optimization firewall (by design)  
5. Hash-manifested reviewer packs  
6. Interactive design studio trajectory  
7. Modern authority overlay versioning (v396–v408+)  
8. Mirage / robust frontier language  

## Where PROCESS still leads (selective MATCH)

1. Coupled plant breadth in one CLI run  
2. TF/PF/CS + SC engineering depth  
3. Machine build consistency catalog  
4. Institutional DEMO/STEP citation density  
5. MFILE ecosystem + scan/VaryRun operational lore  
6. Multi-device heritage (ST / stellarator / IFE)  

---

## Agent / skill kit for this campaign

| Invoke | Role |
|--------|------|
| **`/shams-process-independence`** | **Super-agent** — Phase 0–4 independence director (**auto-run** → push `main`) |
| `/shams-surpass-process` | Sprint orchestrator |
| `/process-specialist` | Upstream PROCESS intelligence |
| `/process-capability-audit` | Domain gap audit |
| `/process-parity-compare` | Numeric / delta dossiers |
| `/architect` `/reactor-systems` `/fusion-performance` `/reviewer` `/developer` `/documentation` | Domain execution |
| `/shams-release-engineer` | Community release gate |

Related docs: **`PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`** (Phase 3.1 canonical), `PROCESS_CROSSWALK.md`, `PROCESS_TO_SHAMS_MAPPING.md`, `PROCESS_lessons.md`, `PROCESS_inspired_upgrade.md`, README § SHAMS vs PROCESS.

---

## Refresh protocol

On each major sprint:

1. Re-fetch PROCESS `process/models/` listing + release tag  
2. Update maturity matrix  
3. Re-rank backlog with evidence  
4. Run parity harness; attach delta dossier hashes  
5. Never claim “PROCESS retired” without scoped evidence from `process_retirement_report`
