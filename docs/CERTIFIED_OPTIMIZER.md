# SHAMS Certified Optimizer (stance)

**Campaign:** Opt Lab / Certified Optimizer Phase 0 (`docs/CERTIFIED_OPTIMIZER_ROADMAP.md`)  
**Pitch:** PROCESS optimizes-and-believes; SHAMS searches-and-certifies.

This page is the studio contract for **philosophy-safe optimization**. Optimization is a **studio capability**, not a truth capability. L0 remains frozen: `Evaluator.evaluate()` → `hot_ion_point()` — same inputs → same outputs; NO-SOLUTION is valid.

**Related:** `docs/CERTIFIED_OPTIMIZER_ROADMAP.md` · `src/extopt/certified_solve.py` (CCFS) · `src/optimization/objective_contract.py` (`objective_contract.v1`) · `src/optimization/opt_run_stamp.py` (`opt_run_stamp.v1`) · `docs/CITE_SHAMS_HANDOFF.md` · independence campaign `docs/PROCESS_SURPASS_ROADMAP.md` (orthogonal — do not blur)

---

## Propose → CCFS contract

Every Opt Lab / Systems Mode / extopt path must obey:

1. **Propose only** — SearchDrivers (LHS, SQP/SLSQP, NSGA-class, surrogate rankers, optional PROCESS) emit `PointInputs` candidates. They do **not** mutate L0 or negotiate hard constraints.
2. **Certify with frozen truth** — every claim is re-evaluated by CCFS / `Evaluator` → `hot_ion`. Surrogate scores and PROCESS MFILE KPIs are never accepted as `VERIFIED`.
3. **Hard fail stays hard** — infeasible candidates are `REJECTED` with `no_solution_atlas.v1` mechanism attribution. FoM never overrides hard constraints.
4. **FoM outside L0** — objectives live in a hashed **ObjectiveContract** (`objective_contract.v1`), never inside `hot_ion`.

```
ObjectiveContract (hashed, outside L0)
  → SearchDriver (propose PointInputs only)
  → CandidateBatch
  → CCFS / Evaluator (frozen re-eval)
  → VerifiedFrontier | RejectedAtlas
  → cite-SHAMS handoff pack
```

---

## Anti-patterns (forbidden)

| Forbidden | Why |
|-----------|-----|
| Optimizer-in-truth (VMCON / fsolve / VaryRun / penalty negotiation inside `Evaluator` → `hot_ion`) | Breaks frozen truth and reproducibility |
| Softening hard constraints so the optimizer “converges” | Masks NO-SOLUTION; false feasibility |
| Certifying surrogate scores or invented MFILE KPIs as `VERIFIED` | Certification without frozen re-eval |
| Putting FoM / objective equations inside `hot_ion` | Blurs studio search with physics truth |
| UI claiming a **true minimum** / true global optimum | Overclaims authority beyond a certified proposal |
| Claiming “PROCESS retired” from Opt Lab work | Independence campaign only; scoped evidence elsewhere |

**Rule of thumb:** if a change makes an optimizer more authoritative than a single frozen evaluation, it is wrong.

---

## UI honesty copy rules

Use these labels (version-tag-free — no `vNNN` in user-facing Opt Lab labels):

| Required language | Forbidden language |
|-------------------|--------------------|
| **Proposed — SHAMS-certified** / “Proposed optimum — SHAMS-certified” | Never: “true minimum,” “true global optimum,” “SHAMS found the real optimum” |
| `VERIFIED` vs `REJECTED` with atlas on rejects | Silent drop of infeasible points |
| Plant KPI honesty watermark on hard-infeasible | Healthy `Pe_net` / COE read as plant-ready when hard-infeasible |
| “Search-and-certify” | “Optimizer-in-truth,” “SHAMS VMCON” |

A certified front is a **set of proposals that passed frozen re-eval**, not a claim that the design space has been exhaustively solved.

**Implementation (Phase 1.3):** shared strings live in `ui_nicegui/lib/certified_opt_honesty.py` (NiceGUI banner + Streamlit parity on Systems Mode / Pareto Lab / Control Room Certified Search). Lock tests: `tests/test_certified_opt_honesty_copy.py`.

---

## ObjectiveContract

FoM / multi-objective definitions are stamped as `objective_contract.v1`:

- Schema + fields: `src/optimization/objective_contract.py`
- Deterministic SHA-256 of canonical JSON — stamp into opt-run artifacts (Phase 1.2)
- Registry bridge: `from_registry_name` / `src/optimization/objectives.py`
- Lock tests: `tests/test_objective_contract_v1.py`

SearchDrivers consume the contract; they never rewrite physics to chase the FoM.

---

## SLSQP / SQP SearchDriver (Phase 2.1–2.3)

Bound-constrained continuous FoM search **outside** L0:

| Item | Detail |
|------|--------|
| Module | `src/optimization/slsqp_search_driver.py` |
| Driver ids | `slsqp` (SciPy SLSQP) · `slsqp_fallback` (pure-Python coordinate descent) |
| API | `run_slsqp_search(base, objective_contract, variables=..., seed=..., force_fallback=...)` |
| Output | `slsqp_search_result.v1` shortlist + `to_ccfs_bundle()` + `stamp_ready()` |
| Hard constraints | SHAMS-evaluated filters / inequalities — **no soft negotiation** |
| Certification | `lightly_certify_shortlist` (shortlist) · **`certify_best_and_neighborhood`** (Phase 2.2: best + seeded local neighborhood → CCFS; stamp + atlas on rejects) |

Neighborhood policy (`neighborhood_certify.v1`): axis-aligned ±`step_frac`×span steps, then seeded random fill; default size 8; clipped to bounds; deterministic for a fixed seed.

### Float policy (Phase 2.3)

SciPy SLSQP may be **platform-sensitive** (SciPy / BLAS / OS). Publication-grade determinism locks prefer:

1. **`force_fallback=True`** → driver id `slsqp_fallback` (pure-Python, seeded)
2. Seeded **neighborhood** proposals (`random.Random(seed)`)
3. **CCFS shortlist / stamp identity** — same seed + `ObjectiveContract` + bounds → same rounded continuous knobs (**8 decimal places**) and same `opt_run_stamp.v1` `stamp_sha256`

The SciPy path (`force_fallback=False`) is smoke-tested only; it is **not** bit-locked across platforms. Cross-platform citeable shortlists should use the fallback driver (or accept platform-local SciPy proposals and always re-certify via CCFS).

Lock tests: `tests/test_slsqp_search_driver.py`, `tests/test_neighborhood_certify.py`, `tests/test_slsqp_determinism.py`.

---

## NSGA-II / MOEA SearchDriver (Phase 3.1)

Propose-only multi-objective search **outside** L0:

| Item | Detail |
|------|--------|
| Module | `src/optimization/nsga2_search_driver.py` |
| Driver ids | `nsga2` (optional pymoo) · `nsga2_fallback` (pure-Python NSGA-II) |
| Contract | `multi_objective_contract.v1` — hashed list of `objective_contract.v1` FoMs |
| API | `run_nsga2_search(base, objective_contracts, variables=..., seed=..., force_fallback=...)` |
| Output | `nsga2_search_result.v1` shortlist + proposed front + `to_ccfs_bundle()` + `stamp_ready()` |
| Hard constraints | Feasible-first constrained domination — **no soft negotiation** |
| Pareto algebra | Reuses `solvers.optimize.dominates` / `pareto_front` |
| Atlas dominatees | **Shipped** (`atlas_dominatee_hook.v1` status=`shipped`); REJECTED / dominated hard-infeasible rows carry `no_solution_atlas.v1` |

**Deps:** pure-Python path needs no new packages. `pymoo` is optional; not added to `requirements.txt`.

Float / determinism policy: publication locks use ``force_fallback=True`` (`nsga2_fallback`) + fixed seed → identical shortlist identity (8 dp knobs) and `stamp_sha256`.

Lock tests: `tests/test_nsga2_search_driver.py`.

---

## Surrogate propose-only SearchDriver (Phase 4.1)

Surrogate ranking is an **accelerator**, never a certifier:

| Item | Detail |
|------|--------|
| Module | `src/optimization/surrogate_propose_search_driver.py` |
| Driver id | `surrogate_propose` |
| Accel | `src/extopt/surrogate_accel.py` (ridge acquisition pool) |
| Overlay | `src/optimization/surrogates.py` (optional ridge predict — untrusted) |
| API | `run_surrogate_propose_search(base, objective_contract, variables=..., seed=..., n_train=..., shortlist_k=...)` |
| Output | `surrogate_propose_search_result.v1` shortlist + `to_ccfs_bundle()` + `stamp_ready()` |
| Certification | **`lightly_certify_shortlist` → CCFS only** — surrogate scores never set `VERIFIED` |
| Honesty | UI/docs: propose-only; “scores never set VERIFIED” |

Training: seeded LHS + frozen `Evaluator` builds tabular rows when `training_records` is omitted. Acquisition ranks a candidate pool; shortlist knobs overlay the baseline `PointInputs`. Claims in the CCFS bundle stay `PROPOSED` with `surrogate_uncertified=true`.

Lock tests: `tests/test_surrogate_propose_search_driver.py`.

---

## Anti L0-opt guardrails (Phase 0.3)

Hard gate: no optimizer / SearchDriver **import path** into frozen truth.

| Scanned L0 consumers | Forbidden import prefixes |
|----------------------|---------------------------|
| `src/evaluator/core.py` (+ sibling evaluator modules) | `optimization` / `src.optimization` |
| `src/physics/hot_ion.py` | `solvers.optimize` / `src.solvers.optimize` |
| | `scipy.optimize` (incl. `from scipy import optimize`) |
| | `extopt` / `src.extopt` (SearchDrivers / CCFS proposers) |

**Allowed:** `src/optimization/`, `src/solvers/`, `src/extopt/` may import and call `Evaluator` / `hot_ion` (propose → certify direction).  
**Forbidden:** the reverse — L0 importing those packages.

| Artifact | Role |
|----------|------|
| `src/optimization/l0_opt_guards.py` | Forbidden-prefix inventory + AST scanner |
| `tests/test_l0_opt_import_guard.py` | Lock tests — **FAIL** if a forbidden import is added to L0 |

### Reviewer checklist (optimizer-in-L0 lens)

When reviewing Opt Lab / Systems Mode / extopt / solvers changes, confirm:

1. No new import of `optimization.*`, `solvers.optimize`, `scipy.optimize`, or `extopt.*` inside `evaluator/` or `hot_ion.py`.
2. `tests/test_l0_opt_import_guard.py` is green (hard gate; docs alone are not enough).
3. SearchDrivers still **propose** `PointInputs` only; certification remains CCFS / frozen `Evaluator`.
4. UI / docs do not claim “true minimum” or PROCESS retirement from this campaign.

---

## Building blocks (reuse, do not rewrite)

| Piece | Path |
|-------|------|
| CCFS firewall | `src/extopt/certified_solve.py` |
| Extopt orchestrator | `src/extopt/orchestrator.py` |
| Frontier intake | `src/extopt/frontier_intake_v406.py` |
| Lightweight propose helpers | `src/solvers/optimize.py` |
| SLSQP SearchDriver (2.1–2.3) | `src/optimization/slsqp_search_driver.py` · `tests/test_slsqp_search_driver.py` · `tests/test_neighborhood_certify.py` · `tests/test_slsqp_determinism.py` |
| NSGA-II SearchDriver (3.1–3.2) | `src/optimization/nsga2_search_driver.py` · `tests/test_nsga2_search_driver.py` |
| Certified-front unify (3.3) | `ui_nicegui/lib/certified_front_viewer.py` · `src/optimization/extopt_contract_bridge.py` · `tests/test_opt_lab_pareto_unify.py` |
| Surrogate propose (4.1) | `src/optimization/surrogate_propose_search_driver.py` · `src/extopt/surrogate_accel.py` · `src/optimization/surrogates.py` · `tests/test_surrogate_propose_search_driver.py` |
| Anti L0-opt import guards | `src/optimization/l0_opt_guards.py` · `tests/test_l0_opt_import_guard.py` |
| Cite handoff | `src/reports/cite_shams_handoff_pack.py` · `docs/CITE_SHAMS_HANDOFF.md` |
| Living roadmap | `docs/CERTIFIED_OPTIMIZER_ROADMAP.md` |

Invoke the campaign: `/shams-certified-optimizer`.

---

## Orthogonality: independence vs Opt Lab

| Campaign | Question | Super-agent |
|----------|----------|-------------|
| **Independence** | Can labs treat SHAMS as default feasibility authority without depending on PROCESS? | `/shams-process-independence` |
| **Certified Optimizer** | Can SHAMS search FoM / Pareto **without** putting optimizers in L0? | `/shams-certified-optimizer` |

PROCESS may appear in Opt Lab only as an **optional proposer** → CCFS. This stance document does **not** claim PROCESS retirement.

---

## Studio entry

- **Opt Lab** deck — three-step certified-search entry (propose→CCFS); shared **certified-front viewer** with Pareto Lab handoff (Phase 3.3)
- Launchpad path: “Start a certified search (Opt Lab)”
- Control Room → Constitution → **Docs Library** → `CERTIFIED_OPTIMIZER.md`
- Launchpad path: “Read certified optimizer stance”
- Point Designer studio entry card → onboarding doc link (version-tag-free label)
- ExtOpt wire: legacy `objective_contract.v3` for `OptimizerJob` **bridged** to Opt Lab `objective_contract.v1` / `multi_objective_contract.v1` via `src/optimization/extopt_contract_bridge.py` (no silent dual-truth FoM)

Lock tests: `tests/test_certified_optimizer_stance.py` · `tests/test_l0_opt_import_guard.py` · `tests/test_opt_lab_entry.py` · `tests/test_opt_lab_pareto_unify.py`.
