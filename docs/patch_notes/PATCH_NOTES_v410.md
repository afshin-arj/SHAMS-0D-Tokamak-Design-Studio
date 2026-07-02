# PATCH NOTES — v410.0.0

## v410.0.0 — Governance & Confinement Consistency Batch (PROPOSAL-002–006)

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-002 — βN constraint wiring

- `src/constraints/constraints.py`: enforce `betaN_proxy` / `beta_N` against `betaN_max` and `betaN_troyon_max` when finite (replaces dead `betaN` key path).

### PROPOSAL-003 — v396 transport envelope Ploss key

- `analysis/transport_envelope_v396.py`: prefer `P_SOL_MW` over `Pin_MW` for IPB98/ITER89-P envelope scalings.

### PROPOSAL-004 — ITER89-P R exponent

- `src/phase1_models.py`: `tauE_iter89p` R exponent **1.5 → 1.2** (published Yushmanov et al. scaling).

### PROPOSAL-005 — v398 overlay evaluation order

- `src/physics/hot_ion.py`: evaluate v398 **after** v397 merge and CS flux fields are in `out` (not at early import time with empty partial dict).

### PROPOSAL-006 — confinement_mult symmetry

- `src/physics/hot_ion.py`: apply `confinement_mult` and profile-family multiplier to `tauE_required_s` / `H_required` same as achieved `tauE_s` / `H98`.

### Regenerated baselines

- `tests/golden/*.json` (10 cases)
- `benchmarks/golden.json`, `benchmarks/golden_artifacts/*.json`
- `src/validation/baselines/baseline_v2230.json` (H98 envelope if changed)

### Expected deltas

- `tauITER89_s`, v396 envelope spread/tiers when enabled
- `H_required` where `confinement_mult` or profile-family mult ≠ 1
- v398 ledger keys when `include_control_stability_authority_v398=True` (e.g. governance_heavy)

Power-balance scalars (`Pin`, `P_SOL`, `Pfus`, `W_MJ`) unchanged except where derived from τE scaling comparators.
