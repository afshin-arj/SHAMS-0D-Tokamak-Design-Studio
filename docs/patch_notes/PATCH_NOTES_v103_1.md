# PATCH NOTES — v103.1 (2026-01-16)

Added:
- tools.ui_self_test: offline, non-Streamlit self-test that exercises UI call paths:
  - baseline PointInputs -> outputs -> constraints -> run artifact
  - schema fallback validation
  - figure export (PNG/SVG)
  - feasibility atlas build
  - sandbox plus run
  - audit pack zip

Unchanged:
- Physics
- Solvers defaults
- UI behavior (no interactive changes)
