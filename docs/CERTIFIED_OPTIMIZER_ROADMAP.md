# SHAMS Certified Optimizer Roadmap

Living campaign document for **philosophy-safe optimization** inside SHAMS.

| Invoke | Role |
|--------|------|
| **`/shams-certified-optimizer`** | **Super-agent** — auto-run next ticket → deep UI/core → push `main` → next step |
| `/pareto-frontier-check` | Frontier / mirage / robust-lane validation |
| `/architect` | Opt Lab seams; propose-only boundary |
| `/shams-process-independence` | Feasibility authority campaign (orthogonal; do not blur) |

**SHAMS version at last refresh:** see `VERSION`  
**Last analytical refresh:** 2026-07-19

## Stance (do not blur)

| | PROCESS | SHAMS Certified Optimizer |
|--|---------|---------------------------|
| Core question | What design optimizes FoM under solvable constraints? | Which **proposed** designs are admissible, and what is the certified feasible set / front? |
| Numerics | VMCON / fsolve **inside** the mutable model graph | Search **outside** L0; every claim re-evaluated by frozen `Evaluator` → `hot_ion` |
| Failure | Avoid / VaryRun / soft negotiation | `REJECTED` + `no_solution_atlas.v1`; FoM never overrides hard constraints |
| “Optimum” | Truth-like from coupled solve | **Certified proposal** only — never more authoritative than a single frozen eval |
| Role of PROCESS | Primary systems optimizer | Optional **proposer** only (CCFS) |

**One-sentence pitch:**

> PROCESS optimizes-and-believes; SHAMS searches-and-certifies.

**Target architecture:**

```
ObjectiveContract (hashed, outside L0)
  → SearchDriver (LHS | SQP/SLSQP | NSGA | surrogate propose | PROCESS)
  → CandidateBatch (PointInputs only)
  → CCFS.verify_all / Evaluator
  → VerifiedFrontier | RejectedAtlas
  → cite-SHAMS handoff pack
```

## Campaign phases

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Stance & contract | **DONE** | 0.1–0.3 complete (ObjectiveContract + stance + anti L0-opt guards) |
| 1 Opt Lab productization | **OPEN** | Unify Systems Mode / Pareto / CCFS packaging |
| 2 Single-objective certified solver | **OPEN** | SQP/SLSQP propose-only; neighborhood re-certify |
| 3 Multi-objective certified front | **OPEN** | NSGA-class + atlas-annotated dominatees |
| 4 Accelerators & external proposers | **OPEN** | Surrogate propose-only; PROCESS→CCFS bridge |
| 5 Cite, robust lanes, exit | **OPEN** | Handoff packs; mirage-safe UQ; campaign exit evidence |

## Non-negotiables

1. Never put VMCON / fsolve / VaryRun / penalty negotiation inside L0.
2. Claims ≠ VERIFIED when hard constraints fail (CCFS hard gate).
3. FoM / objective lives in an **ObjectiveContract** — never inside `hot_ion`.
4. Plant KPIs on hard-infeasible points stay honesty-watermarked.
5. Surrogates and PROCESS may **propose only**; shortlist must re-eval with frozen L0.
6. UI copy: “Proposed optimum — SHAMS-certified,” never “SHAMS found the true minimum.”
7. No version tags (`vNNN`) in user-facing Opt Lab labels.
8. L0 / physics changes need explicit user approval + `/frozen-truth-change`.

## Maturity of existing pieces (reuse, don’t rewrite)

| Piece | Path | Role in campaign |
|-------|------|------------------|
| CCFS | `src/extopt/certified_solve.py` | Certification firewall |
| Extopt orchestrator | `src/extopt/orchestrator.py` | Out-of-process propose → verify |
| Frontier intake | `src/extopt/frontier_intake_v406.py` | Feasible-first / mirage |
| Lightweight opt | `src/solvers/optimize.py` | LHS / random / Pareto helpers |
| Objectives registry | `src/optimization/objectives.py` | FoM names (bridge via `from_registry_name`) |
| ObjectiveContract | `src/optimization/objective_contract.py` | **0.1 DONE** — `objective_contract.v1` + SHA-256 stamp |
| Anti L0-opt guards | `src/optimization/l0_opt_guards.py` | **0.3 DONE** — AST forbidden-import scan; lock tests |
| Surrogate accel | `src/extopt/surrogate_accel.py` | Propose-only acceleration |
| Cite handoff | `src/reports/cite_shams_handoff_pack.py` | Citation unit for verified set |
| Systems Mode / Pareto UI | `ui_nicegui/` + Streamlit | Surfaces to unify into Opt Lab |

---

## Phase 0 — Stance & contract

**Goal:** Architecture and messaging make optimization a **studio capability**, not a truth capability.

| # | Ticket | Done when |
|---|--------|-----------|
| 0.1 | ObjectiveContract schema + hash | **DONE** (2026-07-19) — `src/optimization/objective_contract.py`: stable `objective_contract.v1` (name, sense, metric_keys, bounds_policy, seed_policy, optional notes/provenance/seed); deterministic SHA-256 of canonical JSON; registry bridge via `from_registry_name`; lock tests in `tests/test_objective_contract_v1.py`. Ready to stamp into opt-run artifacts (Phase 1.2). L0 untouched. |
| 0.2 | Certified-optimizer stance docs | **DONE** (2026-07-19) — `docs/CERTIFIED_OPTIMIZER.md`: propose→CCFS contract, anti-patterns (optimizer-in-truth forbidden), UI honesty (“Proposed — SHAMS-certified,” never true minimum), ObjectiveContract pointer, pipeline diagram; linked from README, LIMITATIONS, Docs Library, Launchpad, Studio entry. Lock tests: `tests/test_certified_optimizer_stance.py`. L0 untouched; no PROCESS-retired claim. |
| 0.3 | Anti L0-opt guardrails | **DONE** (2026-07-19) — `src/optimization/l0_opt_guards.py`: forbidden prefixes (`optimization` / `solvers.optimize` / `scipy.optimize` / `extopt`); AST scan of `src/evaluator/*` + `hot_ion.py`; lock tests `tests/test_l0_opt_import_guard.py` FAIL on forbidden L0 imports; reviewer checklist in `docs/CERTIFIED_OPTIMIZER.md`. Packages themselves allowed; L0 consumers forbidden. L0 untouched. |

**Delegates:** `/architect`, `/documentation`, `/developer`, `/reviewer`

**Exit:** A lab can read one page and know SHAMS will never negotiate constraints inside L0. **Phase 0 complete.**

---

## Phase 1 — Opt Lab productization

**Goal:** One verdict-first entry: variables → FoM → run → CCFS front → cite.

| # | Ticket | Done when |
|---|--------|-----------|
| 1.1 | Opt Lab entry surface | NiceGUI Opt Lab (or Systems Mode “Certified search” tab) with clear 3-step path; Streamlit cheap parity |
| 1.2 | Run artifact stamp | Every opt run stores VERSION, objective-contract hash, seed, search driver id, candidate count, VERIFIED/REJECTED counts, pack SHA |
| 1.3 | UI honesty copy | Labels/tooltips never claim true minimum; VERIFIED vs REJECTED + atlas for rejects; no `vNNN` in labels |
| 1.4 | Champion warm-start | One-click load champion `PointInputs` as search seed (propose-only; user/run still certifies) |

**Delegates:** `/architect`, `/developer`, `/nicegui-specialist`, `/ui-specialist`, `/shams-qa-explorer`

**Exit:** User reaches a certified front in minimal clicks without touching PROCESS.

---

## Phase 2 — Single-objective certified solver

**Goal:** PROCESS-familiar continuous search without VMCON-in-truth.

| # | Ticket | Done when |
|---|--------|-----------|
| 2.1 | SLSQP/SQP SearchDriver | Bound-constrained continuous vars; hard constraints as SHAMS-evaluated filters/inequalities (no soft negotiation); SciPy optional with pure-Python fallback |
| 2.2 | Best + neighborhood re-certify | Reported best **and** local neighborhood always go through CCFS; atlas on rejects |
| 2.3 | Lock tests + determinism | Same seed + contract + bounds → same certified shortlist hashes (within documented float policy) |

**Delegates:** `/developer`, `/architect`, `/debugger`, `/fusion-performance`

**Exit:** Single-FoM certified search usable for publication studies.

---

## Phase 3 — Multi-objective certified front

**Goal:** Own the feasible Pareto + NO-SOLUTION story (SHAMS BEAT vs FoM-only PROCESS).

| # | Ticket | Done when |
|---|--------|-----------|
| 3.1 | NSGA-class / MOEA SearchDriver | Propose-only multi-objective; feasible-first; wires existing frontier intake |
| 3.2 | Atlas-annotated dominatees | Rejected / dominated rows carry dominant hard mechanism from `no_solution_atlas.v1` |
| 3.3 | Pareto Lab ↔ Opt Lab unify | One certified-front viewer; `/pareto-frontier-check` gates green |

**Delegates:** `/developer`, `/architect`, `/nicegui-specialist`, skill `/pareto-frontier-check`

**Exit:** Lab can publish a certified multi-objective front with failure mechanisms.

---

## Phase 4 — Accelerators & external proposers

**Goal:** Speed and PROCESS familiarity without trusting non-L0 scores.

| # | Ticket | Done when |
|---|--------|-----------|
| 4.1 | Surrogate propose-only path | Surrogate may rank/propose; **every** shortlist point re-eval with frozen L0; never certify from surrogate |
| 4.2 | PROCESS-as-proposer bridge | Optional IN.DAT/MFILE → map `PointInputs` → CCFS; METHOD-ONLY honesty; no invented MFILE KPIs as truth |
| 4.3 | Extopt orchestrator polish | Out-of-process driver + repo guard + evidence dossier linked to Opt Lab export |

**Delegates:** `/architect`, `/developer`, `/process-specialist`, `/documentation`

**Exit:** Fast search and PROCESS pedigree available; SHAMS remains sole certifier.

---

## Phase 5 — Cite, robust lanes, exit

**Goal:** Certified optimization is citeable and mirage-safe.

| # | Ticket | Done when |
|---|--------|-----------|
| 5.1 | Cite-SHAMS opt handoff | Handoff pack (or extension) for verified front + contract hash + rejected atlas summary |
| 5.2 | Mirage-safe / robust lanes | Optimistic vs robust UQ lanes on certified front; mirages flagged (reuse frontier intake) |
| 5.3 | Campaign exit evidence | Deterministic report: phases 0–5 engineering status; `optimizer_in_l0=false`; no overclaim that “SHAMS replaces VMCON as truth” |

**Delegates:** `/documentation`, `/developer`, `/reviewer`, `/shams-release-engineer`

**Exit:** Engineering complete; community can cite certified Opt Lab runs. Do **not** claim PROCESS retired.

---

## Ranked next tickets (Top 3)

1. **1.1** — Opt Lab entry surface  
2. **1.2** — Run artifact stamp  
3. **1.3** — UI honesty copy  

## Overclaim check

**OK language:** propose-only, CCFS-certified, feasible front, NO-SOLUTION atlas.  
**Forbidden:** optimizer-in-truth, “SHAMS VMCON,” true global minimum, PROCESS retired (use independence campaign for scoped retirement evidence only).
