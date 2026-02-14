# SHAMS–FUSION-X v64 (Physics/solver upgrades + triangularity δ)

## What changed (minimal, additive)

### A) Triangularity **δ** (transparent inboard clearance proxy)
- Added input `delta` (triangularity) to `PointInputs` (default **0.0** → legacy behavior unchanged).
- In the **inboard radial stack closure**, inboard available space is now computed as:
  - `inboard_space = R0 - a*(1 - delta)`
- This is **explicitly a clearance proxy** for compact, shaped designs (documented in code).
- UI: added `δ` input in Point Designer and Systems Mode.

### B) Physics/model outputs (derived quantities as outputs)
- Added derived outputs:
  - `tauE_required_s = W/Ploss`
  - `H_required = tauE_required / tauIPB98`
- Added a *diagnostic* power/confinement self-consistency residual:
  - `power_balance_residual_MW = Ploss - W/tauE_model`
  - `Ploss_from_tauE_model_MW`, `power_balance_tol_MW` (optional cap)

### C) Constraints (optional, off by default)
- New optional constraints (only active when the corresponding cap is finite):
  - `H_required <= H98_allow`
  - `|power_balance_residual_MW| <= power_balance_tol_MW`
  - `betaN_proxy <= betaN_max`
  - `q95_proxy >= q95_min`

### D) Solver robustness
- Added **continuation ladder** solver option (opt-in):
  - `options={"continuation": true, "continuation_stages": [{...}, ...]}`
  - Runs a tolerance ladder using the previous stage solution as the next initial guess.

### E) Semi-analytic Jacobian hooks (tiny, transparent)
- Registered a couple of analytic partials used by `Evaluator.jacobian_targets`:
  - `d(H98)/d(confinement_mult)`
  - `d(Q_DT_eqv)/d(Paux_MW)`

## Backward compatibility
- Defaults preserve prior behavior. All new constraints are **inactive** unless you set caps.
- Existing artifacts remain valid.

- UI/Systems: include `it` and `max_iter` fields in `{event:'fail', reason:'max_iter'}` solver stream events (no behavior change).
