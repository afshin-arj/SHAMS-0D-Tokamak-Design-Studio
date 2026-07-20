# Certified Optimizer — quick reference

## Pitch

PROCESS optimizes-and-believes. SHAMS searches-and-certifies.

## Super-agent

`/shams-certified-optimizer` · skill `/shams-certified-optimizer`

**Default:** auto-run roadmap ticket → **core + physics + UI** integrity → branch/commit/**push `origin/main`** → report next step.  
**Opt-out:** user says `plan-only`, `diagnose-only`, or `no-push`.

## Auto-run loop

```
A Roadmap → B Implement
  → C Core → D Physics → E UI
  → F Reviewer → G Roadmap
  → H Git branch/commit/merge/push origin/main
  → I Next step
```

## Integrity triad (after every upgrade)

| Gate | Minimum |
|------|---------|
| **Core** | CCFS + atlas + L0-opt guard + ticket tests + `verification/run_verification.py` |
| **Physics** | `test_smoke` (+ golden/hot_ion if present); `/plasma-physicist` / `/fusion-performance` when FoM/feasible-first touched |
| **UI** | Opt Lab / Systems / Pareto / CR smoke or explicit “no UI surface”; no `vNNN`; honesty copy |

**Ship only if all three PASS** (then push main).

## Phases

| Phase | Name | Exit |
|-------|------|------|
| 0 | Stance & contract | ObjectiveContract + stance docs + anti L0-opt |
| 1 | Opt Lab productization | One certified-search entry + run stamp |
| 2 | Single-objective | SLSQP/SQP + neighborhood CCFS |
| 3 | Multi-objective | NSGA-class + atlas-annotated front |
| 4 | Accelerators | Surrogate propose; PROCESS→CCFS |
| 5 | Cite & exit | Handoff + robust lanes + exit evidence |

## Key paths

| Artifact | Path |
|----------|------|
| Roadmap | `SHAMS-0D/docs/CERTIFIED_OPTIMIZER_ROADMAP.md` |
| Stance doc | `SHAMS-0D/docs/CERTIFIED_OPTIMIZER.md` |
| CCFS | `SHAMS-0D/src/extopt/certified_solve.py` |
| Orchestrator | `SHAMS-0D/src/extopt/orchestrator.py` |
| Frontier intake | `SHAMS-0D/src/extopt/frontier_intake_v406.py` |
| SearchDrivers | `SHAMS-0D/src/optimization/slsqp_search_driver.py`, `nsga2_search_driver.py` |
| Cite handoff | `SHAMS-0D/src/reports/cite_shams_handoff_pack.py` |
| Git repo | `SHAMS-0D/` (`.git` here) |

## Branch naming

`shams/optlab-<ticket-slug>-YYYYMMDD` → merge → **`git push origin main`** → verify `HEAD == origin/main`

## Subordinate invokes

`/architect` · `/developer` · `/reviewer` · `/plasma-physicist` · `/fusion-performance` · `/nicegui-specialist` · `/ui-specialist` · `/process-specialist` · `/pareto-frontier-check` · `/shams-qa-explorer` · `/documentation` · `/debugger`
