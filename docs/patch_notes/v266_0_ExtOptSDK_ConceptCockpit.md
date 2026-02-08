# SHAMS v266.0 — ExtOpt SDK + Concept Optimization Cockpit

Author: © 2026 Afshin Arjhangmehr

## What shipped (ground truth)

### External Optimization SDK (firewalled)
- New package: `src/extopt/`
- Deterministic batch evaluation of **concept families** (YAML)
- Explicit feasibility-first accounting:
  - hard-feasible boolean (`kpis.feasible_hard`)
  - constraint ledger (dominant blocker mechanism + constraint)
- Optional disk cache (`.shams_extopt_cache/`) as an acceleration feature only
- Evidence pack exporter (design dossier ZIP) per candidate

### Concept Optimization Cockpit (UI)
- New Pareto Lab deck: **Concept Optimization Cockpit**
- Loads concept family YAML (upload or shipped examples)
- Runs batch evaluation using `src/extopt` without modifying frozen truth
- Presents:
  - PASS rate
  - dominant mechanism histogram
  - candidate table
  - per-candidate artifact JSON download
  - on-demand evidence pack ZIP build + download

### Examples
- `examples/concept_families/reactor_intent_baseline.yaml` runnable by the cockpit

## Governance / invariants
- Frozen evaluator unchanged; ExtOpt is an orchestration layer only.
- No hidden iteration; no constraint smoothing; no internal optimization.
- UI helper module import guard upheld (no Streamlit calls at import time).

