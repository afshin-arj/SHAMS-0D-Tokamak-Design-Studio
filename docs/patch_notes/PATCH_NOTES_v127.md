# PATCH NOTES — v127 (2026-01-17)

Study Matrix + Batch Paper Packs.

Added:
- tools:
  - tools.study_matrix:
    - evaluate_point_inputs (hot_ion_point + constraints + run_artifact)
    - build_cases_1d_sweep
    - build_study_matrix_bundle (per-case paper packs + index + master manifest)
  - tools.cli_study_matrix
- UI:
  - Study Matrix + Batch Paper Packs (v127) panel (single UI)
- verify:
  - verify_package imports new tools

Unchanged:
- Physics, constraints, solvers. This is an orchestration/export layer only.
