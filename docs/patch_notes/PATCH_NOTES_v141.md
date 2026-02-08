# PATCH NOTES — v141 (2026-01-18)

Scientific Authority Track A — Robustness Certificate

Added:
- tools.robustness_certificate.generate_robustness_certificate
  - Combines v139 Feasibility Certificate + v140 Sensitivity Report
  - Produces robustness index + per-variable allowable +/- rel changes (when bounded)
  - Provides fragility ranking
- tools.cli_robustness_certificate
- UI: Robustness Certificate (v141) panel (single UI), with Vault export

Safety:
- Downstream only; no physics/solver changes.
