# PATCH NOTES v176.0 — Systems Mode Upgrade

## Systems Mode: usability and performance
- Added a **Systems Mode contract header** that surfaces the SHA256 of:
  - The upstream cached **Point Artifact** (when present)
  - The cached **Systems Artifact** (when present)
- Added an always-available **Systems summary (latest)** so Systems Mode never appears empty.
- Added a **Solve preset** selector:
  - **Robust (recommended):** tighter tolerance, more iterations, smaller trust-region.
  - **Fast:** looser tolerance, fewer iterations, larger trust-region.
- Added **Warm-start** option: uses the last Systems solution as the initial guess for iteration variables.
- Made precheck failure **actionable**: a "Why infeasible?" block explains which hard constraints fail at all corners and which targets are unreachable within bounds, with rule-of-thumb suggestions.
- Added an **Export bundle** download: point artifact + systems artifact JSON (when present).

## Notes
- This release focuses on Systems Mode UX and diagnostics only; physics and feasibility logic are unchanged.
