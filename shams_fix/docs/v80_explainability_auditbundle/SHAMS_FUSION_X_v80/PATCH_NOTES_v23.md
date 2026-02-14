PATCH_NOTES_v23.md

SHAMS–FUSION-X v23 (project-grade upgrades)
==========================================

This release keeps the v22.2 integrated structure intact and adds two major capability upgrades:

1) Requirements + verification harness
-------------------------------------
- New folder: requirements/SHAMS_REQS.yaml
  - Human-readable, versioned requirement statements with acceptance checks.
- New folder: verification/
  - verification/run_verification.py runs:
    - the existing regression harness (benchmarks/run.py)
    - requirement acceptance checks (keys present, baseline feasible, coil-tight infeasible)
  - Writes: verification/report.json
- New pytest gate:
  - tests/test_verification.py runs the verification harness in CI/local pytest.

2) Radial build stack closure (explicit stack solver)
----------------------------------------------------
- New module: src/engineering/radial_stack_solver.py
  - Builds an explicit inboard stack (FW, blanket, shield, VV, gap, TF wind, TF struct)
  - Computes:
    - inboard_space_m = R0 - a
    - spent_noncoil_m (up to and including gap)
    - R_coil_inner_m
    - inboard_build_total_m (full stack)
    - inboard_margin_m
    - radial_build_ok (coil inner radius positive)
    - stack_ok (full stack fits)
  - Optional: simple single-knob repair suggestions (stack_repairs) for UI/reporting.

- Updated: src/physics/hot_ion.py
  - Uses the explicit stack solver, while preserving backward-compatible scalar keys:
    inboard_space_m, spent_noncoil_m, inboard_build_total_m, inboard_margin_m, stack_ok
  - Adds structured outputs:
    radial_stack (list of dicts), stack_repairs (list of suggestions)

Backward compatibility
----------------------
- Existing artifacts and UI consumers that read scalar keys continue to work.
- Benchmarks remain unchanged (curated keys untouched).

How to run verification
-----------------------
From repo root:
  python verification/run_verification.py

To run tests:
  pytest
