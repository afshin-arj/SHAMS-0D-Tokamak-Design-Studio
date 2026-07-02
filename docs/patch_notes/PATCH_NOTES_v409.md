# PATCH NOTES — v409.0.0

## v409.0.0 — L0 Frozen Truth: Thermal Stored Energy Prefactor Correction

Author: © 2026 Afshin Arjhangmehr

### Motivation (Truth Change Record — PROPOSAL-001)

The 0-D thermal stored energy used a prefactor of **3.0** on `n_e (T_i + T_e) V`,
which double-counts the ion and electron contributions relative to the standard
quasi-neutral closure:

\[
W = \tfrac{3}{2} n_e k_B T_e + \tfrac{3}{2} n_i k_B T_i \approx \tfrac{3}{2} n_e (T_i + T_e)
\]

The ion–electron equilibration power term in the same module already used **1.5**
correctly. This release aligns `W_J` with that convention.

### Files touched

- `src/physics/hot_ion.py` — `W_J` prefactor `3.0` → `1.5` (~L711)
- `tests/golden/*.json` — regenerated (10 cases)
- `src/validation/baselines/baseline_v2230.json` — H98 envelope halved
- `benchmarks/golden.json` — regenerated (H98 and W-dependent curated keys)
- `benchmarks/golden_artifacts/*.json` — full run artifacts regenerated
- `docs/PHYSICAL_MODELS_0D.md` — thermal stored energy section added
- `RELEASE_NOTES.md` — v409 entry

### Expected output deltas (~factor 0.5 on W-dependent quantities)

- `W_MJ`, `W_J` — halved
- `tauE_s`, `H98`, `H_required`, `tauE_required_s` — halved (same Ploss, lower W)
- `tau_p_s`, disruption quench severity proxies tied to `W_MJ` — scaled accordingly
- Power-balance scalars (`Pin`, `P_SOL`, `Pfus`, etc.) — **unchanged**

### Golden cases updated

All 10 representative cases under `tests/golden/`.

### Governance

- User-approved frozen-truth change per `GOVERNANCE.md`
- No iteration, smoothing, or constraint negotiation introduced
- Deterministic: same inputs → same outputs (updated baseline)

### Residual risks

- External benchmarks or user scripts that assumed the prior 2× W convention must
  be re-baselined.
- Comparative H98/H_required studies against literature may shift ~2×; physics
  is now aligned with standard 0-D energy accounting.
