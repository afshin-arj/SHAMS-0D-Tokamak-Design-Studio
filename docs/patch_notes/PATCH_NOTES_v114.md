# PATCH NOTES — v114 (2026-01-16)

Preference-Aware Decision Layer (PADL) — post-feasibility scoring + Pareto highlighting (no optimization).

Added:
- tools.preferences:
  - preference payload template + validation
- tools.preference_decision_layer:
  - annotate_candidates_with_preferences: normalizes derived metrics across candidate set and computes explicit composite scores
  - transparent rule-based modifiers (optional)
  - build_pareto_sets: extracts Pareto front(s) over normalized derived metrics
- tools.cli_preference_annotate:
  - offline annotation: outputs candidates_annotated.json, pareto_sets.json, decision_justification.json
- UI (Run Ledger): Preference Sandbox (v114)
  - sliders for weights + optional avoid-rule
  - builds annotation bundle + Pareto sets
  - downloads preferences.json + candidates_annotated.json + pareto_sets.json

Self-test:
- tools.ui_self_test now also produces:
  - preferences.json
  - candidates_annotated.json
  - pareto_sets.json
  - decision_justification.json
  - audit pack includes a summary record

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
