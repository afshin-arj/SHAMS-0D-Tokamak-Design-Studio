# UI Spec: Active Constraints Panel (v69 upgrade)
**Generated:** 2026-01-07

Goal: Make the **active constraint set** always visible in the UI and exports.
This is a *display/export feature only*; no behavior changes.

## Minimum UI requirements
- A dedicated panel/section labeled **Active Constraints**
- Shows:
  - constraint names
  - numeric bounds / target values
  - enabled/disabled status
  - source (default/user override)
- Present in:
  - Systems Mode (required)
  - Point/Scan/Pareto (recommended)
- Included in exported results bundle (`constraints_snapshot.json`)

## Rationale
Interpretability depends on knowing which constraints were imposed.
