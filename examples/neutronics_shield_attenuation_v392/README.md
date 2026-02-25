# v392 — Neutronics Shield Attenuation Authority (Examples)

This folder demonstrates how to enable the **v392.0.0** attenuation-length tightening overlay.

## What v392 does

- Uses a deterministic **exp(-t/λ)** attenuation model (with an optional 1/r² geometric dilution toggle) to propagate a FW fluence proxy to:
  - **TF case** boundary
  - **Cryostat** boundary
  - **Outside bioshield**
- Produces a **dose-rate proxy** outside the bioshield (uSv/h).
- Optional caps (NaN disables) can be used as feasibility constraints.

## Files

- `point_enable_v392.json`: a minimal point JSON enabling v392 with example caps.

## How to run

1. Launch SHAMS UI (`run_ui.cmd` / `./run_ui.sh`).
2. Go to **🧭 Point Designer** and load `point_enable_v392.json`.
3. Run the point evaluation.
4. Inspect:
   - Output scalars: `tf_case_fluence_n_m2_per_fpy_v392`, `cryostat_fluence_n_m2_per_fpy_v392`, `bioshield_dose_rate_uSv_h_v392`.
   - Certification block in Systems Mode (if you run a Systems solve artifact).

## Notes

This is a **screening** authority. It is not a substitute for MCNP/OpenMC-style transport.
