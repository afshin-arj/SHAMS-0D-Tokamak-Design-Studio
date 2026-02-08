# Quantitative Literature Benchmarking
**Updated:** 2026-01-07

## Purpose
Compare SHAMS–FUSION-X outputs to published literature envelopes using the **validation-only** reference library. No tuning is performed; all non-availability of data is reported explicitly.

## Benchmarks

### λq (Heat Flux Width) — Eich 2013 proportionality consistency

Because the Eich 2013 entry in the SHAMS reference library is stored **without an absolute coefficient**, benchmarking is performed via the **coefficient-like normalization**:

`C_Eich = λq * B_tor^{0.8} / ( q95^{1.1} * P_SOL^{0.1} * R_geo )`

If SHAMS follows the proportionality consistently, `C_Eich` should be approximately constant across perturbations.

Computed across golden artifacts: mean `C_Eich = 0.164634`; max spread ≈ **7.61%**.

| Case | λq (mm) | B_tor (T) | q95 | P_SOL (MW) | R_geo (m) | C_Eich | Δ vs mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| sparc_baseline | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |
| sparc_coil_tight | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |
| sparc_current_drive | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |
| sparc_double_null | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |
| sparc_high_Q_target | 0.166947 | 12.20 | 2.2837 | 197.501 | 1.85 | 0.158645 | -3.64% |
| sparc_high_field | 0.150354 | 13.50 | 2.3143 | 148.706 | 1.85 | 0.157079 | -4.59% |
| sparc_impurity_ar | 0.166947 | 12.20 | 2.2837 | 139.424 | 1.85 | 0.164266 | -0.22% |
| sparc_low_aux | 0.166947 | 12.20 | 2.2837 | 101.259 | 1.85 | 0.169605 | +3.02% |
| sparc_pedestal_profile | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |
| sparc_pulsed_20s | 0.166947 | 12.20 | 2.2837 | 124.595 | 1.85 | 0.166124 | +0.91% |

### Bootstrap Fraction — Sauter 1999 (pending numeric extraction)

The Sauter (1999) reference is stored with equation pointers but **numeric extraction of the reference band is not yet present** in the validation-only library.
Until the extraction pass is completed, SHAMS outputs are recorded here for auditability and later comparison.

| Case | f_bs_proxy | I_bs (MA) | Reference band |
|---|---:|---:|---|
| sparc_baseline | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_coil_tight | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_current_drive | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_double_null | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_high_Q_target | 0.261495 | 2.275006 | PENDING_DATA |
| sparc_high_field | 0.183533 | 1.743567 | PENDING_DATA |
| sparc_impurity_ar | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_low_aux | 0.193700 | 1.685190 | PENDING_DATA |
| sparc_pedestal_profile | 0.205806 | 1.790514 | PENDING_DATA |
| sparc_pulsed_20s | 0.205806 | 1.790514 | PENDING_DATA |

### REBCO / HTS Critical Surface Margin (pending reference surface extraction)

The Senatore REBCO critical-surface reference is stored but **numeric parameter extraction is deferred** in the current reference library.
Benchmarking is therefore recorded as **margin metrics** from SHAMS outputs, with pass/fail relative to `margin >= 1.0` (engineering safety convention).

| Case | hts_margin_min | Margin status | Reference surface params |
|---|---:|---|---|
| sparc_baseline | 1.200 | PASS | PENDING_DATA |
| sparc_coil_tight | 1.200 | PASS | PENDING_DATA |
| sparc_current_drive | 1.200 | PASS | PENDING_DATA |
| sparc_double_null | 1.200 | PASS | PENDING_DATA |
| sparc_high_Q_target | 1.200 | PASS | PENDING_DATA |
| sparc_high_field | 1.200 | PASS | PENDING_DATA |
| sparc_impurity_ar | 1.200 | PASS | PENDING_DATA |
| sparc_low_aux | 1.200 | PASS | PENDING_DATA |
| sparc_pedestal_profile | 1.200 | PASS | PENDING_DATA |
| sparc_pulsed_20s | 1.200 | PASS | PENDING_DATA |

### ARC published design point (2015) — pending extraction

The ARC design reference metadata is present, but **published design-point values have not yet been extracted into a structured dataset** in this package.
This section remains explicitly pending until the extraction is completed.

| Quantity | SHAMS–FUSION-X | Literature (ARC) | Deviation |
|---|---:|---:|---:|
| R0 (m) | TBD | TBD | TBD |
| a (m) | TBD | TBD | TBD |
| B0 (T) | TBD | TBD | TBD |
| Ip (MA) | TBD | TBD | TBD |
| Pfus (MW) | TBD | TBD | TBD |
| Q | TBD | TBD | TBD |

## Notes
- Deviations are reported, never hidden.
- `PENDING_DATA` indicates the reference metadata exists but numeric extraction has not yet been embedded in this package.
