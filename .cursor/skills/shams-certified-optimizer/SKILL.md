---
name: shams-certified-optimizer
description: Master playbook to ship philosophy-safe optimization inside SHAMS (Opt Lab / Certified Optimizer). On invoke, AUTOMATICALLY executes the next roadmap ticket, then MUST pass UI + physics + core integrity gates, then branches/commits/merges and pushes origin/main on GitHub, and reports the next step. Use when adding SQP/NSGA/Pareto search, ObjectiveContract, CCFS-certified fronts, PROCESS-as-proposer, surrogate propose-only, or continuing the certified-optimizer campaign.
disable-model-invocation: true
---

# SHAMS Certified Optimizer (Master Playbook)

Ship **search-and-certify** optimization inside SHAMS **without** changing frozen-truth philosophy.

**Super-agent:** `/shams-certified-optimizer`  
**Living roadmap:** `SHAMS-0D/docs/CERTIFIED_OPTIMIZER_ROADMAP.md`

**Pitch:** PROCESS optimizes-and-believes; SHAMS searches-and-certifies.

Related (subordinate) skills: `/pareto-frontier-check`, `/shams-feature-development`, `/shams-test-suite`, `/physics-review`, `/reviewer-pack-export`, `/shams-full-product-qa`, `/process-parity-compare` (PROCESS proposer only), `/frozen-truth-change` (only if L0 — normally never)

Orthogonal campaign: `/shams-process-independence` (feasibility authority / PROCESS role). Do **not** merge roadmaps; reuse CCFS / atlas / cite-pack as building blocks.

## Default mode: AUTOMATIC EXECUTION

Unless the user says **plan-only**, **diagnose-only**, or **no-push**, every invoke runs:

```
A Roadmap → B Implement
  → C Core integrity → D Physics integrity → E UI integrity
  → F Reviewer → G Roadmap edit
  → H Git branch + commit + merge + push origin/main
  → I Next step
```

**After every upgrade:** integrity triad (core + physics + UI) is mandatory.  
**After every successful upgrade:** create branch, commit, merge, and **push `origin/main`** (unless `no-push`).

Do not stop at planning. Pause only for L0 approval, secrets, or explicit user stop flags.

## Stance (never blur)

| | Forbidden | Required |
|--|-----------|----------|
| L0 | VMCON / fsolve / VaryRun / negotiation inside `Evaluator`→`hot_ion` | Frozen re-eval of every claim |
| FoM | Objective inside physics truth | `ObjectiveContract` hashed, outside L0 |
| Surrogate / PROCESS | Certify from surrogate or MFILE KPIs | Propose `PointInputs` only → CCFS |
| UI | “True minimum” / version tags in labels | “Proposed — SHAMS-certified” + atlas on rejects |
| Honesty | Healthy Pe_net on hard-infeasible | Plant KPI watermark + REJECTED |

## Target pipeline

```
ObjectiveContract → SearchDriver → CandidateBatch → CCFS / Evaluator
  → VerifiedFrontier | RejectedAtlas → cite-SHAMS handoff
```

## Non-negotiables

1. Never put optimizers inside L0.
2. CCFS: claims ≠ VERIFIED when hard constraints fail.
3. FoM lives only in ObjectiveContract / registry — never in `hot_ion`.
4. Surrogates propose only; shortlist always re-evals frozen L0.
5. PROCESS is optional proposer; no invented MFILE numbers as truth.
6. No `vNNN` in user-facing Opt Lab labels.
7. Physics/L0 changes need explicit user approval.
8. Never force-push `main`; stage explicit paths only.
9. Never ship without **core + physics + UI** integrity (UI may be documented “no UI surface”).
10. Always branch + commit + **push `origin/main`** after a successful ticket (unless `no-push`).

## Master checklist

```
Certified Optimizer campaign:
- [ ] Phase 0 — Stance & contract
- [ ] Phase 1 — Opt Lab productization
- [ ] Phase 2 — Single-objective certified solver
- [ ] Phase 3 — Multi-objective certified front
- [ ] Phase 4 — Accelerators & external proposers
- [ ] Phase 5 — Cite, robust lanes, exit
- [ ] Roadmap + overclaim check updated

Each auto-run:
- [ ] A — Roadmap diagnose + ONE ticket
- [ ] B — Implement
- [ ] C — Core integrity PASS
- [ ] D — Physics integrity PASS
- [ ] E — UI integrity PASS
- [ ] F — Reviewer PASS
- [ ] G — Roadmap updated
- [ ] H — Branch + commit + merge + push origin/main
- [ ] I — Next step told to user
```

---

## Phase tickets (summary)

Full tables live in `docs/CERTIFIED_OPTIMIZER_ROADMAP.md`.

| Phase | Tickets | Exit |
|-------|---------|------|
| 0 Stance | 0.1 ObjectiveContract · 0.2 stance docs · 0.3 anti L0-opt guards | Lab knows opt ≠ truth |
| 1 Opt Lab | 1.1 entry · 1.2 run stamp · 1.3 honesty copy · 1.4 champion warm-start | Certified front in few clicks |
| 2 Single-obj | 2.1 SLSQP/SQP driver · 2.2 neighborhood CCFS · 2.3 determinism locks | Publication-grade FoM search |
| 3 Multi-obj | 3.1 NSGA driver · 3.2 atlas dominatees · 3.3 unify Pareto Lab | Certified multi-obj + mechanisms |
| 4 Accel | 4.1 surrogate propose · 4.2 PROCESS→CCFS · 4.3 orchestrator polish | Fast + pedigree; SHAMS certifies |
| 5 Exit | 5.1 cite handoff · 5.2 robust/mirage · 5.3 exit evidence | Citeable Opt Lab; no overclaim |

**Default first ticket if all open:** **0.1 ObjectiveContract schema + hash**  
**Current next (after Phase 0–2 + 3.1 on `main`):** **3.2 — Atlas-annotated dominatees**

---

## Routing table (always use)

| Work | Agent | Skill |
|------|-------|-------|
| Seams / Opt Lab architecture | `/architect` | — |
| ObjectiveContract / SearchDriver / CCFS wiring | `/developer` | `/shams-feature-development` |
| Frontier / mirage / robust lanes | `/architect` + `/developer` | `/pareto-frontier-check` |
| FoM / KPI interpretation | `/fusion-performance` | `/point-design-eval` |
| PROCESS-as-proposer honesty | `/process-specialist` | `/process-parity-compare` |
| NiceGUI Opt Lab / Systems Mode | `/nicegui-specialist` | `/ui-panel-author` |
| Streamlit parity | `/ui-specialist` | `/ui-panel-author`, `/streamlit-visual-qa` |
| Stance / Opt Lab docs | `/documentation` | — |
| Physics integrity | `/plasma-physicist` | `/physics-review`, `/point-design-eval` |
| Audit after change | `/reviewer` | — |
| Tests / NaNs | `/debugger` | `/shams-test-suite`, `/numerical-debug` |
| Deep product UI | `/shams-qa-explorer` | `/shams-full-product-qa` (scoped) |
| Cite / release packaging | `/documentation` + `/shams-release-engineer` | `/reviewer-pack-export` |
| L0 change (rare — usually refuse) | — | `/frozen-truth-change` + user approval |

Spawn specialists **in parallel** when independent (e.g. architect seam map + documentation stance draft while developer scaffolds contract).

---

## Integrity triad (Stages C–E) — after every upgrade

### C — Core integrity

```powershell
cd SHAMS-0D
python -m pytest tests/test_ccfs_verified_hard_gate.py -v
python -m pytest tests/test_no_solution_atlas.py -v
python -m pytest tests/test_l0_opt_import_guard.py -v
python -m pytest tests/test_extopt_frontier_intake_v406.py -v
python -m pytest <ticket tests> -v
python verification/run_verification.py
# when change is broad:
python -m pytest
```

Confirm `evaluator/core.py` / `physics/hot_ion.py` untouched (unless approved frozen-truth change).  
Required: fix failures before Stage H. `/reviewer` runs in Stage F with **optimizer-in-L0** lens.

### D — Physics integrity

Always run after every upgrade (even UI-only tickets):

```powershell
cd SHAMS-0D
python -m pytest tests/test_smoke.py -v
# Plus nearest golden / hot_ion / confinement locks present in the repo
```

| When | Delegate |
|------|----------|
| FoM / metrics / feasible-first / neighborhood / NSGA | `/plasma-physicist` (readonly) |
| Q / Pe_net / ObjectiveContract metrics | `/fusion-performance` |
| NaNs / nondeterminism | `/debugger` + `/numerical-debug` |

Minimum ship gate: smoke PASS + verification PASS + L0-opt import guard PASS. Name every physics suite run in the report — never silently skip.

### E — UI integrity

| Ticket touch | Required UI depth |
|--------------|-------------------|
| Opt Lab / Systems Mode / Pareto | NiceGUI entry + certified-front viewer; Streamlit parity if touched |
| Run stamp / export / cite | Control Room / export / handoff buttons |
| Honesty copy | Confirm no “true minimum”; REJECTED+atlas visible |
| Docs-only | Docs Library link smoke OR explicit “no UI surface” |

Prefer `/nicegui-specialist` + scoped `/shams-qa-explorer`. No P0/P1 ship blockers. No `vNNN` in labels.

## Git ship (Stage H) — MANDATORY to GitHub main

Repo: `SHAMS-0D/` (not parent `SHAMS/` unless that tree has `.git`).

```powershell
cd SHAMS-0D
git checkout main
git pull --ff-only origin main
git checkout -b shams/optlab-<ticket-slug>-YYYYMMDD
git add <explicit ticket + test + roadmap paths only>
git commit -m @"
<phase.ticket>: <why in one line>

Certified Optimizer auto-run (/shams-certified-optimizer).
Core: <pass summary>
Physics: <pass summary>
UI: <pass summary>
L0 risk: none
"@
git push -u origin HEAD
git checkout main
git pull --ff-only origin main
git merge shams/optlab-<ticket-slug>-YYYYMMDD -m "Merge Opt Lab ticket: <why>"
git push origin main
git fetch origin
# Require: git rev-parse HEAD == git rev-parse origin/main
```

**Skip Stage H only if:** user said `no-push`, or integrity triad / reviewer failed, or only L0 proposals exist.  
Do **not** report ticket complete with `main pushed: no` unless `no-push` was requested.

## Next step (Stage I)

Always end with **one** next ticket:

```markdown
### Next step
**Ticket:** <next from roadmap>
**Why:** <one line>
**Invoke:** `/shams-certified-optimizer`
```

## Deliverable template

```markdown
## Certified Optimizer — auto-run report
### Ticket completed
### Core / Physics / UI integrity
### Reviewer
### Git (branch, sha, origin/main pushed)  ← must be yes unless no-push
### Roadmap
### Next step
### Overclaim check
```

## Anti-patterns (block immediately)

- Shipping SQP/NSGA that mutates or bypasses `Evaluator.evaluate`
- Softening hard constraints so the optimizer “converges”
- Certifying surrogate scores or PROCESS MFILE KPIs as VERIFIED
- UI claiming global true optimum
- Blurring this campaign with “PROCESS retired”
- Breadth chase (new physics) instead of certification packaging
- Shipping without core + physics + UI integrity
- Claiming done without pushing `origin/main`
- Stopping after “here’s the plan” on a full invoke

## Subordinate skills

- Frontier / mirage only → `/pareto-frontier-check`
- Feature impl → `/shams-feature-development`
- Tests → `/shams-test-suite`
- Physics review → `/physics-review` + `/plasma-physicist`
- Product UI depth → `/shams-full-product-qa` (scoped) + `/shams-qa-explorer`
- PROCESS proposer honesty → `/process-parity-compare`
- Independence / retirement → `/shams-process-independence` (separate)
