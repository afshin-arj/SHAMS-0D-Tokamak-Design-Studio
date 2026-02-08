# PATCH NOTES — v111 (2026-01-16)

Design Family Explorer (additive; no optimization).

Added:
- tools.design_family:
  - build_design_family_report: safe local exploration inside a feasible topology island (component)
  - produces design_family_report.json with per-sample inputs + feasibility + worst limiting constraint
- UI (Run Ledger): Design Family Explorer (v111)
  - pick baseline run artifact + component index + sample count + radius
  - generates and downloads design_family_report.json
- tools.ui_self_test now also produces:
  - design_family_report.json
  - audit pack includes this artifact

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
