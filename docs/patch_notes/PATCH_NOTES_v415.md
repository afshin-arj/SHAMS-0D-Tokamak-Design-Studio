# PATCH NOTES — v415.0.0

## v415.0.0 — Studio improvement audit (constraint parity + UI choke point)

Author: © 2026 Afshin Arjhangmehr

### Constraint ledger parity (PROPOSAL-013)

- `constraints/system.py`: mirror v397 `q0_proxy` + `bootstrap_localization` caps in PROCESS ledger.
- `constraints/system.py`: mirror v399 Zeff, Prad fraction, and detachment margin caps (fraction logic matches governance).
- `constraints/system.py`: mirror v398 stability caps (carried from studio audit batch).
- `constraints/constraints.py`: granular v403 neutronics caps (DPA, He appm, cooldown, TBR, fast attenuation).
- Remove duplicate `detachment_index` ledger row (v285 vs v287).

### UI / infrastructure

- `ui/robust_pareto_lab.py`: route point evaluation through `Evaluator` choke point (extends PROPOSAL-008).
- `ui/app.py`: replace deprecated `datetime.utcnow()` with timezone-aware UTC stamp.
- `certification/stability_control_certification_v374.py`: timezone-aware UTC timestamp.

### Tests

- `tests/test_top5_audit_fixes.py`: v397/v399 ledger parity, detachment dedup.
- `tests/test_ui_evaluator_choke_point.py`: robust Pareto lab AST guard.

### Not modified

L0 physics equations, golden JSON, `hot_ion.py` truth path.
