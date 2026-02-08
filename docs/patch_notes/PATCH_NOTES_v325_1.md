# SHAMS v325.1 — Hygiene & UI Interop Audit Hardening

Author: © 2026 Afshin Arjhangmehr

This patch release hardens the **release hygiene** and adds runtime protections
to prevent unwanted cache artifacts from appearing in packaged builds.

## Fixes

- Enforced repo hygiene by adding `scripts/hygiene_clean.py` and running it
  automatically in `run_ui.cmd` and `run_ui.sh`.
- Added `sitecustomize.py` (best-effort) and `tests/conftest.py` guard to set
  `PYTHONDONTWRITEBYTECODE=1` and `sys.dont_write_bytecode=True`.
- Added a deterministic hygiene gate (`tests/test_repo_hygiene.py`) to prevent
  shipping cache artifacts.

## Notes

- This patch **does not change physics truth** or any evaluator closures.
- It only affects working-tree cleanliness and packaging safety.
