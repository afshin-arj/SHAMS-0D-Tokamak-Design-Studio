# PATCH NOTES — v117 (2026-01-16)

Tolerance Envelope (deterministic uncertainty/tolerance analysis).

Added:
- schemas:
  - shams_tolerance_envelope_report.schema.json
- tools.tolerance_envelope:
  - template_tolerance_spec
  - evaluate_tolerance_envelope: center + corners + (optional) edge midpoints (deterministic)
  - envelope_summary_csv
- tools.cli_tolerance_envelope:
  - offline envelope analysis from a saved run artifact
- UI:
  - Tolerance Envelope (v117) panel
    - select baseline run artifact
    - set tolerances (relative or absolute)
    - run envelope and download report/CSV
- Self-test:
  - generates tolerance_envelope_report_v117.json and tolerance_envelope_summary_v117.csv
  - audit pack includes tolerance envelope summary

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
