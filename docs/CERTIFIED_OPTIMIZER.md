# SHAMS Certified Optimizer (stance)

**Campaign:** Opt Lab / Certified Optimizer Phase 0 (`docs/CERTIFIED_OPTIMIZER_ROADMAP.md`)  
**Pitch:** PROCESS optimizes-and-believes; SHAMS searches-and-certifies.

This page is the studio contract for **philosophy-safe optimization**. Optimization is a **studio capability**, not a truth capability. L0 remains frozen: `Evaluator.evaluate()` → `hot_ion_point()` — same inputs → same outputs; NO-SOLUTION is valid.

**Related:** `docs/CERTIFIED_OPTIMIZER_ROADMAP.md` · `src/extopt/certified_solve.py` (CCFS) · `src/optimization/objective_contract.py` (`objective_contract.v1`) · `docs/CITE_SHAMS_HANDOFF.md` · independence campaign `docs/PROCESS_SURPASS_ROADMAP.md` (orthogonal — do not blur)

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

---

## ObjectiveContract

FoM / multi-objective definitions are stamped as `objective_contract.v1`:

- Schema + fields: `src/optimization/objective_contract.py`
- Deterministic SHA-256 of canonical JSON — stamp into opt-run artifacts (Phase 1.2)
- Registry bridge: `from_registry_name` / `src/optimization/objectives.py`
- Lock tests: `tests/test_objective_contract_v1.py`

SearchDrivers consume the contract; they never rewrite physics to chase the FoM.

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

- **Opt Lab** deck — three-step certified-search entry (propose→CCFS); routes into Systems Mode / Pareto Lab / Control Room Certified Search
- Launchpad path: “Start a certified search (Opt Lab)”
- Control Room → Constitution → **Docs Library** → `CERTIFIED_OPTIMIZER.md`
- Launchpad path: “Read certified optimizer stance”
- Point Designer studio entry card → onboarding doc link (version-tag-free label)

Lock tests: `tests/test_certified_optimizer_stance.py` · `tests/test_l0_opt_import_guard.py` · `tests/test_opt_lab_entry.py`.
