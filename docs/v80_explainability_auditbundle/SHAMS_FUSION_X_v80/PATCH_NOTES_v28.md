# PATCH NOTES — v28 (PROCESS-inspired closures + studies + envelope)

## Added engineering closures (transparent proxies)
- TF magnet pack proxy: `src/engineering/magnets/pack.py`
  - Adds current-density limit, stress margin, cryo power coupling.
- TBR proxy: `src/engineering/neutronics_proxy/tbr.py`
- Divertor proxy v2 with tech modes: `src/engineering/heat_exhaust/divertor.py`
- Availability proxy: `src/availability/model.py`
- Component CAPEX proxy: `src/economics/components/stack.py`

All proxies are *transparent* and tracked with model cards under `src/model_cards/`.

## Integrated into point evaluation
`src/physics/hot_ion.py` now emits:
- `tf_*`, `cryo_power_MW`
- `TBR*`
- `q_parallel_*`, `Psep_MW`
- `availability*`
- `capex_*`

## Constraints
`src/constraints/system.py` now promotes the above to constraints so they participate in:
- dominant blocker reporting
- feasibility frontier and nudges
- solver trade ledger

## Studies + Envelope
- New CLI tools:
  - `tools/studies/scan.py`
  - `tools/studies/constraint_sweep.py`
  - `tools/studies/scenario_sweep.py`
  - `tools/envelope_check.py`
- Streamlit: Studies tab includes an **Operating envelope check** panel.

## Docs/UI updates
- Updated `docs/PHYSICAL_MODELS_0D.md` with Phase-2 closures.
- New docs:
  - `docs/ENGINEERING_CLOSURES.md`
  - `docs/ENVELOPE.md`
  - `docs/STUDIES.md`
