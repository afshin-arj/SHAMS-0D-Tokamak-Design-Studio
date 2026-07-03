# PATCH NOTES — v418.0.0

## v418.0.0 — PROPOSAL-026–028 + PHYS-003/008–010 + UI sprint

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-026 — Registry code-generation

- `src/constraints/registry_codegen.py`: generates `authority_specs_codegen.py` from `authority_caps.json`.
- `load_authority_specs()` prefers codegen module (PROPOSAL-026).
- Root proxy shims for import stability.

### PROPOSAL-027 — Constraint pipeline diff UI

- `src/constraints/pipeline_diff.py`: `build_pipeline_diff_dossier()`.
- `ui/constraint_pipeline_diff.py`: side-by-side registry / legacy / merged governance panel.
- Wired in Point Designer Constraint Briefing tab.

### PROPOSAL-028 — NO-SOLUTION mechanism atlas

- `src/diagnostics/no_solution_atlas.py`: `build_no_solution_atlas()`, `classify_mechanism()`.
- `ui/no_solution_atlas_ui.py`: mechanism atlas panel in Constraint Briefing.

### PHYS-003 — v402 reference thresholds in authority dashboard

- `render_v402_threshold_panel()` in `ui/authority_dashboard.py`.
- Thresholds written to session and merged into `PointInputs` before evaluate.

### PHYS-008 — phase1_models H-mode in v396 envelope

- `analysis/transport_envelope_v396.py`: Mirnov + Shimomura H-mode scalings when `LH_ok` / H-mode regime.
- Emits `transport_envelope_regime_v396`.

### PHYS-009 — ELM duty-cycle → availability ledger

- Schema: `elm_duty_cycle_v409`, `elm_recovery_downtime_frac_v409`.
- `elm_transient_heat_v409.py` emits `elm_availability_downtime_frac_v409`.
- `hot_ion.py` couples downtime into `availability_model` when v409 enabled.

### PHYS-010 — Tritium tight-closure reactor preset

- `src/schema/governance_presets.py`: reactor intent defaults `include_tritium_tight_closure=True` with caps.
- UI checkbox and design-intent change handler apply preset.

### UI sprint

- Authority dashboard: v408/v409/v405 toggles, v402 thresholds, overlay session writeback.
- `merge_overlay_session_into_inputs()` applied before Point Designer evaluate.
- τE peaking factor display via `render_profile_tau_peaking_panel()` in trace hook.

### Golden regression

- Regenerated for `transport_envelope_regime_v396` and evaluation path parity.

### Tests

- 187 pytest pass; verification pass.
