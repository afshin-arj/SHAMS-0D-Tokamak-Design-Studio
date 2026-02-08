# PATCH NOTES — v94.1 (2026-01-08)

Bugfix release (no physics/solver changes).

Fixed:
- `src/shams_io/run_artifact.py` now imports blockers using package-relative import so offline tools (`verify_figures`, plot tests) run from repo root.
- `tools.verify_package` now skips Streamlit UI import when `streamlit` is not installed (offline/minimal environments).

Unchanged:
- Physics
- Solvers
- Defaults
