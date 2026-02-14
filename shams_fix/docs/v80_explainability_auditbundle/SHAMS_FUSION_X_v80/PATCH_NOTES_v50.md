# PATCH NOTES v50 — PROCESS-inspired “first-class decks, studies, registries” (non-breaking)

This upgrade is **additive** and preserves SHAMS’ core philosophy:
transparent proxies, feasibility-before-optimization, constraint-first, and
artifact-driven reproducibility.

## Added

### Case Deck v1 (deterministic input → resolved config)
- New schema: `case_deck.v1` (YAML/JSON)
- New tool: `tools/run_case_deck.py`
- New CLI: `shams deck <case_deck.yaml> --out case_out/`
- Emits `run_config_resolved.json` plus embeds the resolved config + SHA256
  fingerprint in the run artifact.

### Study index + summary as first-class artifacts
- `study_out/index.json` now includes:
  - `schema_version: study_index.v1`
  - `provenance` (platform/python/commit/version)
- New `study_out/study_summary.json` (`study_summary.v1`) with quick decision
  summary fields.

### Constraint Margin Ledger
- Run artifacts now include `constraint_ledger` (`constraint_ledger.v1`)
  with stable fingerprinting and “top blockers” extraction.
- Summary PDF adds a dedicated ledger page.

### Model registry and model set
- Artifacts now embed `model_registry` (`model_registry.v1`) and `model_set`
  (`model_set.v1`) to keep model-option selection explicit and auditable.

### Verification checks (unit/sanity audit proxy)
- Artifacts now embed `verification_checks` (`verification_checks.v1`).

### Scenario delta
- Scenario artifacts now include `scenario_delta` (`scenario_delta.v1`) showing
  changed inputs and a small KPI delta subset.

## Backward compatibility
- All fields are additive; existing consumers can ignore new keys.
