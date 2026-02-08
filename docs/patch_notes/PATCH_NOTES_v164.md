# PATCH NOTES — v164 (2026-01-18)

Sensitivity + Bottleneck Attribution (Finite Differences)

Adds v164 local sensitivity analysis around a witness:
- tools.sensitivity_v164: build_sensitivity_report() + render_sensitivity_markdown()
- tools.cli_sensitivity_v164
- UI panel: Sensitivity + Bottleneck Attribution (v164) integrated after v163, before v160
- ui_self_test produces sensitivity_v164.json and sensitivity_v164.md

Safety:
- Downstream-only; strict evaluation budget (1 + 2*N evals).
- No physics or solver logic changes.
