# PATCH NOTES — v109 (2026-01-16)

Component-local causality (additive).

Added:
- tools.component_dominance:
  - build_component_dominance_report: assigns feasible run artifacts to feasible islands
  - computes dominance per component and aggregates failure modes near each component
- UI (Run Ledger): Island Inspector (v109)
  - builds per-component report and downloads JSON
- tools.ui_self_test now also produces:
  - component_dominance_report.json
  - audit pack includes this artifact

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
