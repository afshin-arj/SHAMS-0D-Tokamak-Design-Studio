# PATCH NOTES — v417.0.0

## v417.0.0 — PROPOSAL-024–025 + PHYS-002 + PHYS-004–006

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-024 — Certification deterministic regression harness

- `tests/test_certification_deterministic.py`: deterministic digest stubs for v352, v374, v376, v388, v389; module smoke for all 16 certification modules.
- Fixes certification API mismatches (`out=` vs `outputs=`, `evaluate_*` vs `certify_*`, v352 `run_uq_fn` stub).

### PROPOSAL-025 — Single-source authority constraint registry

- `src/constraints/data/authority_caps.json`: canonical cap specs for v396–v409, v403, v405, v407, v408.
- `src/constraints/authority_registry.py`: `load_authority_specs()`, `evaluate_registry_governance()`, `evaluate_registry_ledger()`.
- `constraints/unified.py`: merges registry pipeline with legacy governance/ledger builders.
- `tests/test_authority_registry.py`.

### PHYS-002 — Density peaking → τE coupling (L0, approved)

- `profile_proxy_v397.py`: `_tau_e_peaking_factor()`, emits `tau_e_density_peaking_factor_v397`, `tau_e_profile_factor_v397`.
- `hot_ion.py`: when `profile_proxy_v397_enabled`, scales `tauE_s` / `tauE_eff_s` and recomputes `H98`.
- `tests/test_v397_tau_peaking.py`.

### PHYS-004 — ELM / transient heat-load overlay (v409)

- `src/analysis/elm_transient_heat_v409.py` + shim.
- Schema: `include_elm_transient_heat_v409`, caps, `elm_energy_fraction_v409`, `elm_duration_ms_v409`.
- `hot_ion.py`: overlay before v402 dominance.
- Registry caps for ELM transient heat flux.

### PHYS-005 — Tritium tight-closure authority (v405)

- `src/analysis/tritium_tight_closure_authority_v405.py` + shim (wraps `fuel_cycle/tritium_authority.py`).
- Registry caps for in-vessel inventory, total inventory, TBR effective when `include_tritium_tight_closure`.

### PHYS-006 — CD mix → plant electric ledger (v408)

- `src/analysis/cd_mix_plant_ledger_v408.py` + shim.
- Schema: `P_cd_eccd_max_MW`, `P_cd_lhcd_max_MW`.
- `hot_ion.py`: overlay before v402; emits `P_cd_eccd_el_MW`, `P_cd_lhcd_el_MW`, `cd_mix_frac_sum`.
- `tests/test_overlays_v408_v409.py`.

### Golden regression

- Regenerated `tests/golden/*.json` for additive CD-mix schema echo keys (disabled-by-default overlays).

### Tests

- 176 pytest pass; verification and golden pass.
