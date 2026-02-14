# PATCH NOTES — v140 (2026-01-18)

Constraint Sensitivity Maps (Scientific Authority Track A)

Added:
- tools.sensitivity_maps
  - SensitivityConfig, run_sensitivity: finite perturbations (+/-) per variable to find feasibility break boundary
  - build_sensitivity_bundle: JSON + CSV + optional plot + manifest -> zip
- tools.cli_sensitivity_maps
- UI: Sensitivity Maps (v140) panel integrated in single UI
- Vault export support for sensitivity bundle

Safety:
- No physics/solver changes. Uses existing evaluator only.
