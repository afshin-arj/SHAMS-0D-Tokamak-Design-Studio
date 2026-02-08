# PATCH NOTES — v122 (2026-01-17)

Explainability Layer (L4) — narrative and causality summaries (post-processing only).

Added:
- schemas:
  - shams_explainability_report.schema.json
- tools:
  - tools.explainability.build_explainability_report
  - tools.cli_explainability
- UI:
  - Explainability (v122) panel (replaces placeholder call)
  - layer registry updated to point to v122 panel
  - optionally uses in-session mission report (v121) and tolerance envelope report (v117) if available
- Self-test:
  - generates explainability_report_v122.json and explainability_report_v122.txt

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior and workflows
