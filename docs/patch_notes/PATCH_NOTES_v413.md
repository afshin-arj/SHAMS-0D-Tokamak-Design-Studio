# PATCH NOTES — v413.0.0

## v413.0.0 — Post-v412 audit safe fixes (constraint wiring + tests)

Author: © 2026 Afshin Arjhangmehr

### Constraint pipeline hygiene

- `constraint_is_hard()` — respect `severity` field (fixes Monte Carlo / nudge paths treating soft as hard).
- `evaluate_constraints()` — add v401/v403 min-margin enforcement mirroring PROCESS ledger.
- `system.py` — v403 `nm_min_margin_frac_v403` wired with `lo_key=nm_fragile_margin_frac_v403`; disambiguate duplicate `"TF peak field"` name.

### Schema / overlay

- `nm_fragile_margin_frac_v403` input + echoed in v403 outputs.

### Infrastructure

- `evaluator/core.py` — remove dead duplicate import branch.
- `certification/stability_control_certification_v374.py` — dual import fallback.

### Tests

- `tests/test_constraint_severity.py`
- `tests/test_certification_smoke_v374.py`

No L0 physics or golden drift.
