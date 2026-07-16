# PATCH NOTES — v420.0.0

## v420.0.0 — Availability → OPEX / LCOE coupling authority (Independence Phase 2.4)

Author: © 2026 Afshin Arjhangmehr

### MATCH-as-overlay

- New authority: `availability_opex_lcoe_authority_v420` (`include_availability_opex_lcoe_authority_v420`, OFF by default).
- One explicit availability chain with recorded provenance
  (`availability_v368` → `availability_v359` → `availability_cert_v391` → `availability_model` (ELM v409-coupled) → `inp.availability`)
  feeds operating hours → annual net energy → annual OPEX → LCOE **on the same hours basis**.
- Fixes the historical mismatch where v360 OPEX electricity terms used the legacy hours basis
  while the v360 LCOE energy denominator preferred v368/v359 energy. Frozen v359/v360/v368
  stamped outputs are untouched; v420 cross-checks them and reports informational residuals.
- OPEX formulas centralized in `src/economics/opex_coupling.py` (single source; no duplicated
  economics equations). Tritium processing OPEX availability-coupled (365 × A × duty days).
- LCOE decomposition (CAPEX / replacement / OPEX shares) with bookkeeping identity checks;
  `avail_v420_consistency_ok` gates on bookkeeping checks only.
- PROXY provenance everywhere; transparent in-repo coefficients — **not** 1990 Generomak,
  no invented PROCESS MFILE numbers.
- `avail_v420_LCOE_USD_per_MWh` registered in `plant_kpi_honesty.v1` LCOE aliases —
  hard-infeasible points display "— (diagnostic)", never a healthy LCOE.

### Wiring

- PointInputs flag + optional caps (`availability_min_v420`, `lcoe_max_USD_per_MWh_v420`,
  `opex_max_MUSD_per_y_v420`, `avail_opex_lcoe_consistency_tol_v420`).
- `hot_ion.py` post-process overlay after v419 (empty patch when OFF — no L0 / golden drift).
- Optional hard caps in `authority_caps.json` (+ regenerated codegen, 32 specs; regen also resynced a pre-existing JSON↔codegen count drift).
- Run-artifact economics table exports v420 chain keys when present.
- UI: NiceGUI mission snapshot / control contracts / Suite authority ledger
  (availability→energy→OPEX→LCOE chain table with PROXY badges + honesty watermark notes),
  authority dashboard toggle, Point Designer authority toggle/labels.

### Tests

- `tests/test_availability_opex_lcoe_authority_v420.py` (15 tests: precedence/provenance,
  same-hours coupling, LCOE decomposition, consistency gating, determinism, caps echo,
  flag-off L0 no-drift via Evaluator, honesty interplay, constraint registration).

### L0 risk

None — overlay only; flag OFF returns `{}`.
