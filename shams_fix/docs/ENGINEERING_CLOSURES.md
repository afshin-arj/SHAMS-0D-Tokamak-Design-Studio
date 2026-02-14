# Engineering closures (PROCESS-inspired)

This document summarizes the new *closure* proxies that turn SHAMS from point physics into a systems code that
is driven by constraints and margins.

## TF magnet pack proxy
- Module: `src/engineering/magnets/pack.py`
- Key outputs:
  - `tf_Jop_MA_per_mm2`, `tf_Jop_limit_MA_per_mm2`
  - `tf_stress_MPa`, `tf_stress_allow_MPa`
  - `cryo_power_MW`

## Tritium breeding ratio proxy (TBR)
- Module: `src/engineering/neutronics_proxy/tbr.py`
- Key outputs: `TBR`, `TBR_required`, `TBR_margin`, `TBR_validity`

## Divertor heat exhaust proxy
- Module: `src/engineering/heat_exhaust/divertor.py`
- Key outputs: `Psep_MW`, `q_parallel_MW_per_m2`, `q_parallel_limit_MW_per_m2`
- Modes: conservative / baseline / aggressive

## Availability model proxy
- Module: `src/availability/model.py`
- Key outputs: `availability`, planned/forced outage fractions

## Constraint integration
These outputs are converted into constraints in `src/constraints/system.py` so they participate in:
- solve reports
- dominant blocker ranking
- feasibility frontier and nudges


## Economics proxies (authority + uncertainty) — v232

`src.economics.cost.cost_proxies()` remains a **transparent proxy** and does not drive feasibility unless an explicit cost gate is enabled.

New fields emitted when economics is enabled:

- `cost_authority_tier`: `parametric | external`
- `cost_coeffs_sha256`: SHA-256 of user cost-coeff JSON when provided
- `cost_validity_domain`: free-text scope statement (defaults to “relative proxy”)
- Component uncertainty bands (1σ, default fractions overridable via cost calibration JSON):
  - `cost_*_MUSD_low/high`
  - `CAPEX_proxy_MUSD_low/high`
- Dominance / fragility signals:
  - `dominant_cost_driver`
  - `dominant_cost_frac`
  - `cost_fragility_index` (≡ dominant fraction)

These additions are **descriptive** unless used as explicit feasibility screens in Systems/Scan policy.
