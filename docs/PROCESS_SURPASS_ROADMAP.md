# SHAMS ↔ PROCESS Surpass Roadmap

Living campaign document. Orchestrator skill: `/shams-surpass-process`. Specialist: `/process-specialist`.

**Upstream:** [ukaea/PROCESS](https://github.com/ukaea/PROCESS) · [docs](https://ukaea.github.io/PROCESS/)  
**SHAMS version at last refresh:** see `VERSION`  
**Last analytical refresh:** 2026-07-16

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
| Magnets / radial build | **Partial / proxy** | v400 ON; depth below PROCESS TF/PF |
| Plant ledger / power | **Proxy** | Closure hooks exist |
| Divertor / exhaust | **Proxy** | PROCESS also thin — BEAT target |
| Neutronics / TBR | **Proxy** | v401/v407/v408 scaffolding |
| Economics | **Proxy** | Do not clone 1990 Generomak as truth |
| Neutrals / edge | **Missing** | |
| PROCESS numeric parity corpus | **Stub** | Harness strong; reference cases weak |
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
| 3 | PROCESS parity corpus + delta dossiers | BEAT | no | M | H | `/process-parity-compare` |
| 4 | Plant power ledger honesty (gate Pe_net on hard feasibility) + Sankey audit | MATCH | no | M | H | `/reactor-systems` |
| 5 | Exhaust / divertor authority depth | BEAT | no | M | H | `/reactor-systems` |
| 6 | Magnet / SC / PF–CS overlay depth (post-v400) | MATCH | no | L | H | `/reactor-systems` |
| 7 | Radial-build closure narrative | MATCH | no | M | M | `/architect` |
| 8 | Native UQ / mirage-safe robust lanes | BEAT | no | L | H | `/pareto-frontier-check` |
| 9 | Availability → OPEX / LCOE coupling | MATCH | no | M | M | `/reactor-systems` |
| 10 | Bottom-up modular costing (not 1990 Generomak) | MATCH | no | L | M | `/shams-feature-development` |
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
2. Ship NO-SOLUTION atlas on every infeasible artifact (`src/diagnostics/no_solution_atlas.py`)  
3. Fill `benchmarks/parity/process_reference_cases.json` (≥1 real PROCESS ref + hashed delta dossier; no invented MFILE)

### Minimum DEMO MATCH overlays (reactor-systems)

1. TF/PF/CS SC depth beyond v400  
2. Radial / machine-build closure  
3. Plant Sankey-grade ledger (extend v408)  
4. Availability → energy/OPEX  
5. Bottom-up modular costing auth  

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
| `/process-specialist` | Upstream PROCESS intelligence |
| `/shams-surpass-process` | Sprint orchestrator |
| `/process-capability-audit` | Domain gap audit |
| `/process-parity-compare` | Numeric / delta dossiers |
| `/architect` `/reactor-systems` `/fusion-performance` `/reviewer` | Domain execution |

Related docs: `PROCESS_CROSSWALK.md`, `PROCESS_TO_SHAMS_MAPPING.md`, `PROCESS_lessons.md`, `PROCESS_inspired_upgrade.md`, README § SHAMS vs PROCESS.

---

## Refresh protocol

On each major sprint:

1. Re-fetch PROCESS `process/models/` listing + release tag  
2. Update maturity matrix  
3. Re-rank backlog with evidence  
4. Run parity harness; attach delta dossier hashes  
5. Never claim “PROCESS retired” without scoped evidence from `process_retirement_report`
