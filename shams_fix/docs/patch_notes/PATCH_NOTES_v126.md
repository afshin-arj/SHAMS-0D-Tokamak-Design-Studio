# PATCH NOTES — v126 (2026-01-17)

UI Smoke Runner + Scenario Matrix.

Added:
- tools:
  - tools.ui_smoke_runner.run_smoke (headless Streamlit stub runner)
  - tools.cli_ui_smoke
- UI:
  - UI Smoke & Diagnostics panel (v126)
- schemas:
  - shams_paper_pack_manifest.schema.json already present (v125)
  - (no new runtime schema required for smoke report)

Notes:
- Smoke checks are lightweight and designed to catch import/render errors.
- This does not replace regression suites or interactive manual verification.

Unchanged:
- Physics, constraints, solvers.
