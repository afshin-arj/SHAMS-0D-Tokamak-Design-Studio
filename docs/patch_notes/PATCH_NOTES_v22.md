# PATCH_NOTES_v22.md

This release upgrades SHAMS–FUSION-X v21 (Streamlit Point Designer sync fix preserved) into an **integrated program-grade** baseline.

## Fixed
- Streamlit import-time crash: `_sync_point_designer_from_last_point_inp()` is now invoked only after it is defined (prevents `NameError`).

## Added (Program-grade upgrades)
### 1) Lifecycle costing (transparent proxy)
- New module: `src/economics/lifecycle.py`
- Extended economics outputs (backward compatible):
  - `LCOE_proxy_USD_per_MWh`
  - `NPV_cost_proxy_MUSD`
- Default calibration file updated: `docs/cost_calibration_default.json`

### 2) Scenario comparison
- New package: `src/scenarios/` (`spec.py`, `runner.py`)
- New tool: `tools/run_scenarios.py`

### 3) Robustness under uncertainty
- `src/analysis/uncertainty.py` upgraded to report:
  - metric quantiles / stats
  - feasibility probabilities
  - threshold probabilities
- Solver/evaluator wiring updated to keep artifacts decision-grade.

### 4) Design-space navigation nudges (feasibility-first)
- New module: `src/frontier/nudges.py`
- New tool: `tools/nudge_point.py`
- Frontier init upgraded: `src/frontier/__init__.py`

### 5) Calibration registry + provenance discipline
- New module: `src/calibration/registry.py` (+ `src/calibration/__init__.py`)
- `src/calibration/calibration.py` upgraded to support registry-style factor application.
- Evaluator now records applied calibration factors in artifacts (`src/evaluator/core.py`).

## PROCESS learning (doc-first mapping, no code-style import)
- `docs/PROCESS_TO_SHAMS_MAPPING.md`
- Upgrade guides:
  - `docs/UPGRADE_STAGE2_SCENARIOS.md`
  - `docs/UPGRADE_STAGE3_ROBUST_UQ.md`
  - `docs/UPGRADE_STAGE4_NAVIGATION_NUDGES.md`
  - `docs/UPGRADE_STAGE5_CALIBRATION_REGISTRY.md`
