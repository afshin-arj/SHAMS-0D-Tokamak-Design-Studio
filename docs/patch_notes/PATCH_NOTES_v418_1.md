# PATCH NOTES — v418.1.0

## v418.1.0 — Golden regression fidelity fix + PHYS-010 tritium golden capture

Author: © 2026 Afshin Arjhangmehr

### Problem

`tests/test_golden_physics_outputs.py` failed 10/10 cases with a key-set drift:
32 "missing" authority-overlay keys + 13 "added" tritium keys.

### Root cause (test-fidelity bug, NOT a physics regression)

`src/physics/hot_ion.py` imports its authority overlays via `from ..contracts.*` /
`from ..analysis.*` / `from ..engineering.*` relative imports. These resolve only
when `hot_ion` is imported as `src.physics.hot_ion` (i.e. `src` resolved as a
package, the layout the L0 evaluator uses). When imported as top-level
`physics.hot_ion` (with `<repo>/src` on `sys.path`), the two-dot relative imports
raise "attempted relative import beyond top-level package"; the surrounding bare
`except Exception:` blocks swallow the error and the overlays silently no-op,
dropping ~32 output keys:

- magnet-tech contract: `J_eng_max_A_mm2`, `Tcoil_min_K`, `Tcoil_max_K`,
  `P_tf_ohmic_max_MW`, `coil_heat_nuclear_max_MW`, `B_peak_allow_T`,
  `sigma_allow_MPa`, ...
- v389 structural-stress: `cs_*`, `tf_struct_margin_*`, `vv_struct_margin_*`,
  `structural_margin_ledger_v389`, ...
- impurity radiation: `impurity_*`
- neutronics-materials: `neutronics_materials_*`

The application runtime is unaffected: `src/evaluator/core.py` imports
`from ..physics.hot_ion import hot_ion_point` (src-as-package), so all overlays
load correctly. Verified directly by running `Evaluator.evaluate()` on golden
cases — all overlay keys present, `magnet_regime` correct (HTS/CU).

The golden TEST, however, imported `from physics.hot_ion import hot_ion_point`
(top-level) — a context the app never uses, where overlays silently fail. The
golden JSON files were generated in the app (`src.*`) context, so the test was
comparing app-context golden vs top-level-context current → drift.

The 13 "added" tritium keys are the documented **PHYS-010** tritium tight-closure
preset (`src/schema/governance_presets.py`, `src/fuel_cycle/tritium_authority.py`),
committed in v418.0.0. The v418 golden regen was incomplete — it only regenerated
for `transport_envelope_regime_v396` and missed PHYS-010's tritium outputs.

### Fix

1. `tests/test_golden_physics_outputs.py`: import `PointInputs` and
   `hot_ion_point` as `src.models.inputs` / `src.physics.hot_ion` to pin the SAME
   import context the L0 evaluator choke point uses. No `src/` physics code
   changed (`git diff src/` empty).
2. Regenerated golden: `python tests/test_golden_physics_outputs.py --regen`.

### Golden diff

10 files changed, **130 insertions(+), 0 deletions(-)**. Each file gained exactly
13 lines — the PHYS-010 tritium tight-closure keys. No value changes, no other
key changes:

`TBR_eff_fuelcycle`, `TBR_self_sufficiency_margin`, `TBR_self_sufficiency_required`,
`T_in_vessel_max_kg`, `T_in_vessel_required_kg`, `T_inventory_reserve_kg`,
`T_loss_fraction`, `T_processing_delay_days`, `T_startup_inventory_kg`,
`T_total_inventory_max_kg`, `T_total_inventory_required_kg`,
`include_tritium_tight_closure`, `tritium_fuelcycle_validity`.

### Validation

- Full `pytest`: 187 pass, 0 fail.
- Plasma-physicist readonly sign-off on the golden diff + test-fidelity fix.

### Known pre-existing tech debt (NOT addressed here; out of scope)

`hot_ion.py`'s dual-import coverage is incomplete: ~20+ overlay imports use bare
`from ..X` relative imports without a top-level fallback (cf. the established
dual-import pattern at lines 36–63 for `models`/`profiles`). Consequently the
top-level `physics.hot_ion` import context (used by
`benchmarks/update_golden_artifacts.py` and several tests that do
`from physics.hot_ion import ...`) silently drops those overlays. This is the
AUD-005 / PROPOSAL-012 incomplete-coverage gap. The application runtime is not
affected (it uses the `src.*` package context). A dedicated robustness pass to
complete the dual-import fallbacks is recommended as a separate, versioned change.
