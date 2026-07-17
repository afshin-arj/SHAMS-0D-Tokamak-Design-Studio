# PROCESS → SHAMS Migration Guide

**Audience:** Labs and reviewers who currently run UKAEA [PROCESS](https://github.com/ukaea/PROCESS) and want to reproduce (or replace) a feasibility study in SHAMS without depending on PROCESS as the authority.  
**Campaign:** Independence Phase 3.1 (`docs/PROCESS_SURPASS_ROADMAP.md`)  
**SHAMS version:** see repository root `VERSION`  
**Status:** Community default documentation — **does not** claim PROCESS retirement.

Related (do not duplicate poorly — use this guide as the entry point):

| Doc | Role |
|-----|------|
| `PROCESS_CROSSWALK.md` | Short conceptual crosswalk |
| `PROCESS_TO_SHAMS_MAPPING.md` | Domain checklist (cost, magnets, build, …) |
| `PROCESS_lessons.md` / `PROCESS_inspired_upgrade.md` | Architecture lessons |
| `LIMITATIONS.md` | Honest scope / what SHAMS does **not** claim |
| `benchmarks/parity/` | METHOD-ONLY (or NUMERIC) parity corpus + dossiers |

---

## 1. Stance in one paragraph

**PROCESS** asks: *what design optimizes a figure of merit if constraints can be negotiated inside a coupled solver?*  
**SHAMS** asks: *which designs are admissible under explicit constraints, why others fail, and what evidence can be cited without trusting the optimization path?*

Migration is therefore **not** “re-run IN.DAT until MFILE numbers match.” Migration is:

1. Map intent → SHAMS inputs / case / constraint policy  
2. Evaluate with frozen L0 (`Evaluator.evaluate()` → `hot_ion_point`)  
3. Treat **NO-SOLUTION** as valid science  
4. Cite `VERSION` + artifact hashes  
5. Optionally keep PROCESS as an **external proposer** only (CCFS)

---

## 2. Workflow map (PROCESS → SHAMS)

```
PROCESS                              SHAMS
───────                              ─────
IN.DAT / defaults                    PointInputs (+ Case / study intent)
DataStructure (mutable)              Immutable run artifact snapshot
VMCON / fsolve inside models         Solvers / Systems Mode / extopt
                                     → propose PointInputs only
Constraint negotiation / penalties   Hard / diagnostic / ignored (explicit)
OUT.DAT / MFILE.DAT                  Run artifact JSON (+ exports, reviewer packs)
“Best design” / FoM optimum          Not a SHAMS truth concept
                                     (Pareto / explore = propose, then re-certify)
```

**Single choke point (never bypass):** `src/evaluator/core.py` → `src/physics/hot_ion.py`.  
Same inputs → same outputs. No hidden solvers, smoothing, or infeasibility masking inside L0.

---

## 3. IN.DAT concepts → SHAMS Case / PointInputs

PROCESS packs geometry, plasma, engineering, plant, and integer switches into IN.DAT. SHAMS separates **point physics knobs** (`PointInputs` in `src/schema/inputs.py`) from **governance / exploration** (constraint tiers, authority overlays, Systems Mode bounds).

### 3.1 Core plasma / machine knobs (typical first map)

| PROCESS-style concept (illustrative) | SHAMS `PointInputs` field | Units / notes |
|--------------------------------------|---------------------------|---------------|
| Major radius | `R0_m` | m |
| Minor radius | `a_m` | m |
| Elongation | `kappa` | — |
| Toroidal field on axis | `Bt_T` | T |
| Plasma current | `Ip_MA` | MA |
| Ion temperature (0-D) | `Ti_keV` | keV |
| Greenwald fraction | `fG` | — |
| Auxiliary power | `Paux_MW` | MW |
| Confinement scaling choice | `confinement_scaling` | e.g. `IPB98y2`, `ITER89P` |
| Profile / bootstrap scaffolding | `profile_model`, `bootstrap_model`, … | Explicit; defaults preserve 0-D |

This table is a **conceptual** map. Variable names and integer switches in PROCESS are far denser; do not invent missing PROCESS values. Prefer: (a) your lab’s documented IN.DAT meaning, then (b) SHAMS field docstrings / `VOCABULARY_LEDGER.md`.

### 3.2 Case / study intent (beyond a single point)

| PROCESS habit | SHAMS analogue |
|---------------|----------------|
| One IN.DAT + ioptimz mode | Point Designer run, or System Suite / Scan Lab campaign |
| Iteration variables + bounds | Explore / Systems Mode bounds (propose-only) |
| Objective / FoM | External objective only — never inside L0 |
| Integer model switches | Explicit `PointInputs` enums / authority overlay flags (OFF by default) |

### 3.3 Practical recipe

1. Export or note the **physical** knobs you care about from IN.DAT (R0, a, B, Ip, n/T proxies, Paux, …).  
2. Enter them in **Point Designer** (or construct `PointInputs` in Python).  
3. Set constraint enforcement policy (hard vs diagnostic) — see §5.  
4. Evaluate once; if infeasible, read `no_solution_atlas.v1` — do not retune L0.  
5. Only then optionally run Systems Mode / CCFS with PROCESS (or another optimizer) as proposer.

---

## 4. MFILE / OUT.DAT → SHAMS artifacts

| PROCESS output | SHAMS artefact | How to use |
|----------------|----------------|------------|
| MFILE.DAT / OUT.DAT tables | Run artifact JSON (`build_run_artifact` / deck export) | Feasibility, outputs, constraints, provenance |
| Solver “converged” flag | Hard-feasibility + CCFS `VERIFIED` / `REJECTED` | Convergence ≠ admissible |
| Scan / VaryRun families | System Suite / Scan Lab campaign artifacts | Atlas + first-kill narratives |
| Cost / plant summary lines | Plant ledger overlays + `plant_kpi_honesty.v1` | Watermark when hard-infeasible |
| Hand-off to other codes | `tools/interoperability/process_handoff.py` → `process_handoff.json` | SHAMS **upstream** auditor → optional PROCESS-like proposer |

**Honesty rule:** Never invent PROCESS MFILE numbers for “parity.” If no licensed MFILE extract is available, use **METHOD-ONLY** dossiers under `benchmarks/parity/` and say so.

### 4.1 What to look for on a SHAMS run artifact

- `inputs` — frozen `PointInputs` snapshot  
- `outputs` — L0 metrics (Q, powers, …)  
- `constraints` — ledger with tiers and margins  
- `no_solution_atlas.v1` — present on hard-infeasible / CCFS REJECTED paths  
- `plant_kpi_honesty.v1` — watermark so infeasible points do not look like healthy `Pe_net` / COE  
- Manifest / SHA-256 when exporting reviewer packs  

---

## 5. Constraint / policy mapping

PROCESS often folds limits into penalty terms and solver negotiation. SHAMS makes policy explicit:

| PROCESS-ish behavior | SHAMS policy |
|----------------------|--------------|
| Hard engineering limit that must not be violated | Constraint tier **hard** — failure ⇒ NO-SOLUTION / CCFS REJECTED |
| Soft preference / monitoring | **Diagnostic** (soft) — reported, non-blocking for VERIFIED |
| Turned off / unused limit | **Ignored** (or overlay OFF) — still document in study notes |
| q95 / Greenwald enforcement knobs | `q95_enforcement`, `greenwald_enforcement` on `PointInputs` (`hard` \| `diagnostic`) |
| Plant / magnet depth via PROCESS modules | Versioned **authority overlays** (OFF by default); never silent L0 mutation |

Registry / bookkeeping: `src/constraints/registry.py`, `src/constraints/constraints.py`.  
Governance UI: Control Room → Constitution → Constraints / Constraint Provenance.

**Do not** soften hard constraints to “converge like PROCESS.”

---

## 6. CCFS — PROCESS as propose-only

Certificate-Carrying Feasibility Solver (`src/extopt/certified_solve.py`):

1. External client (PROCESS, NSGA, human, …) **proposes** candidate `PointInputs` (+ optional claims).  
2. SHAMS **re-evaluates** with frozen truth.  
3. `VERIFIED` requires hard-feasible governance constraints. Claims never force VERIFIED.  
4. `REJECTED` / infeasible rows carry `no_solution_atlas.v1`.

Migration implication: you may keep PROCESS in the loop for **search**, but SHAMS remains the **feasibility authority**. Publishing a study that only cites MFILE without SHAMS re-certification is the old dependency pattern this campaign retires *as authority* — not as software that must be deleted.

---

## 7. How to cite VERSION + artifact hashes

For any feasibility claim intended for review or publication:

1. Record the SHAMS `VERSION` file string (also mirrored in `CITATION.cff`).  
2. Export the run / campaign artifact (and reviewer pack when available).  
3. Cite **SHA-256** hashes of the artifact JSON and/or export manifest.  
4. State constraint policy and which authority overlays were ON.  
5. If comparing to PROCESS, attach a parity dossier and declare **METHOD-ONLY** or **NUMERIC** status.

Example citation posture (adapt to your style guide):

> Feasibility evaluated with SHAMS `<VERSION>` (frozen L0). Run artifact SHA-256 `<hash>`. Hard constraints: \<policy\>. PROCESS used only as optional proposer / legacy reference; SHAMS CCFS status: VERIFIED|REJECTED.

See also `CITATION.cff` and `docs/LIMITATIONS.md` § Citation posture.

---

## 8. METHOD-ONLY parity honesty

Independence Phase 1 shipped a **METHOD-ONLY** PROCESS parity corpus:

- `benchmarks/parity/process_reference_cases.json` (`process.parity_cases.v2`)  
- Hashed dossiers under `benchmarks/parity/dossiers/`  
- Harness: `src/parity_harness/process_corpus.py`

**METHOD-ONLY** means: SHAMS inputs, diagnostics, and mapping assumptions are recorded; PROCESS numeric KPIs are **intentionally null** until a lab contributes a licensed, provenance-tagged MFILE/OUT.DAT extract.

Rules:

- Do **not** invent MFILE / OUT.DAT numbers.  
- Do **not** tune H98 / L0 to hit unpublished PROCESS targets.  
- Do **not** claim numeric parity or “PROCESS retired” from METHOD-ONLY evidence alone.  
- NUMERIC upgrade path: contribute a real reference pack + delta dossier; keep assumption registry explicit (`/process-parity-compare`).

---

## 9. Studio entry points (UI)

| Intent | Where |
|--------|--------|
| Single-point feasibility | Point Designer |
| Campaign / plant KPI views | System Suite |
| Docs / constraint governance | Control Room → Constitution → **Docs Library** (open this guide) |
| Cross-code semantics (docs-level) | Publication Benchmarks (not numeric PROCESS) |
| Optional PROCESS JSON compare | System Suite benchmark / parity tab (upload lab extract; no invented numbers) |
| SHAMS → PROCESS-like handoff JSON | `tools/interoperability/process_handoff.py` (CLI / legacy Streamlit interoperability panel) |

This guide is documentation-first; Control Room → Constitution → Docs Library defaults to `PROCESS_TO_SHAMS_MIGRATION_GUIDE.md` when present. Launchpad also offers “Migrate a PROCESS study to SHAMS.”

---

## 10. Anti-patterns (block these)

- Putting VMCON / fsolve / VaryRun **inside** L0  
- Soft-landing NO-SOLUTION to look like PROCESS convergence  
- Inventing PROCESS reference numbers for plots or dossiers  
- Claiming “PROCESS retired” without a scoped `process_retirement_report` + evidence  
- Showing healthy `Pe_net` / COE on hard-infeasible points without watermark  
- Treating MATCH overlays (magnets, build, plant, cost) as L0 truth when flags are OFF  

---

## 11. Suggested migration checklist

- [ ] Read stance (§1) and `LIMITATIONS.md`  
- [ ] Map IN.DAT knobs → `PointInputs` (§3); record assumptions  
- [ ] Set hard/diagnostic policy (§5)  
- [ ] Evaluate; if infeasible, archive atlas + dominant mechanisms (§4)  
- [ ] Export artifact; record `VERSION` + SHA-256 (§7)  
- [ ] Optional: PROCESS propose → CCFS certify (§6)  
- [ ] Optional: METHOD-ONLY or NUMERIC parity dossier (§8)  
- [ ] Do **not** claim PROCESS retirement  

---

## 12. Where to go next

| Need | Path / invoke |
|------|----------------|
| Roadmap / campaign status | `docs/PROCESS_SURPASS_ROADMAP.md` |
| Zenodo / citation cut | Phase 3.2 — `/shams-process-independence` |
| Champion cases | Phase 3.3 |
| Domain depth checklist | `PROCESS_TO_SHAMS_MAPPING.md` |
| Upstream PROCESS inventory | `/process-capability-audit` |

---

*Independence Phase 3.1 — community migration guide. Feasibility authority stays with SHAMS; PROCESS remains optional proposer / legacy reproduce.*
