# TF coil stress and strain proxies (screening)

SHAMS includes *transparent, 0-D* TF coil engineering proxies intended for **feasibility screening**, not detailed design.

## Outputs (from the point model)

- `tf_stress_MPa`  
  Thin-shell hoop-stress proxy at the TF inner leg:
  - magnetic pressure: `p = B_peak^2 / (2*mu0)`
  - stress: `sigma ≈ p * R_inner / t_struct`
  - optional multiplier: `tf_struct_factor`

- `tf_strain`  
  Linear elastic strain proxy:
  - `eps = sigma / E`
  - uses `tf_E_GPa` (effective modulus)

Related diagnostics:
- `tf_stress_allow_MPa`, `tf_stress_margin_MPa`
- `tf_strain_allow`, `tf_strain_margin`

## Optional feasibility caps

These caps are **OFF by default** unless you set them explicitly:

- `tf_stress_allow_MPa` (default 900 MPa)
- `tf_strain_allow` (default NaN → disabled)

## Notes / limitations

- `B_peak` is mapped from `Bt` using a 1/R inner-leg scaling with `Bpeak_factor`.
- Real stress/strain depends on coil case design, preload, grading, joints, etc.
- These proxies are designed to be replaced by higher-fidelity models later while keeping auditability.


## HTS critical-surface margin (Jc(B,T,ε)/Jop)

- Disabled by default: set `include_hts_critical_surface=true` to compute `hts_margin_cs`.
- Purpose: expose an explicit, auditable margin computed from a lightweight REBCO-like fit `Jc(B,T)` and a Gaussian strain degradation using the *computed* TF strain proxy `tf_strain`.
- Operating demand is an engineering current density `Jop` estimated from ampere-turns required for `Bt_T` at `R0_m` divided by winding-pack area proxy `A_wp ≈ t_tf_wind_m * (2*kappa*a)`.
- Outputs:
  - `hts_Jop_A_m2`, `hts_Jc_A_m2`
  - `hts_operating_fraction = Jop/Jc_eff`
  - `hts_margin_cs = Jc_eff/Jop`
- Constraint: when enabled, the existing `hts_margin_min` threshold applies to `hts_margin_cs` (in addition to the legacy `hts_margin`).


## TF operating current density from winding-pack geometry (optional)

By default, SHAMS uses the input `tf_Jop_MA_per_mm2` as the TF operating current density.

If you set:

- `tf_Jop_from_wp_geometry = True`

then SHAMS computes an *engineering* current density from the required ampere-turns and an explicit winding-pack area proxy:

- Required ampere-turns for on-axis field:
  - `N*I = 2π R0 Bt / μ0`
- Winding-pack height proxy:
  - `H_wp = tf_wp_height_factor * (a * κ)`
- Winding-pack conducting area proxy:
  - `A_wp = tf_wp_width_m * H_wp * tf_wp_fill_factor`
- Engineering current density:
  - `J_eng = (N*I) / A_wp`

The model reports:
- `tf_ampere_turns_MAturn`, `tf_I_turn_MA`
- `tf_wp_area_mm2`, `tf_wp_height_m`
- `tf_Jop_geom_MA_per_mm2`, `tf_Jop_source`

This is a **screening proxy** for feasibility studies; it is intentionally explicit and conservative.

