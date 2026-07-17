# PATCH NOTES — v421.0.0

## v421.0.0 — Bottom-up modular costing authority (Independence Phase 2.5)

Author: © 2026 Afshin Arjhangmehr

### MATCH-as-overlay

- New authority: `bottom_up_costing_authority_v421` (`include_bottom_up_costing_authority_v421`, OFF by default).
- Modular direct/indirect CAPEX **account ledger** — 13 reviewer-auditable rows, each with
  explicit driver, driver value, units, unit rate, and kind (equipment / direct-fraction / indirect):
  magnets, blanket & first wall, divertor, vacuum vessel, cryostat/cryoplant, heating & CD,
  tritium plant / fuel cycle, power conversion / BOP, buildings & site, remote handling,
  instrumentation & control, engineering & management, contingency.
- Unit rates and fractions are transparent in-repo screening proxies (echoed in the patch as
  `costing_v421_unit_rates` / `costing_v421_fractions`) — **not** a port of the 1990
  Generomak / PROCESS cost accounts, and no invented PROCESS MFILE numbers.
- Mass drivers prefer stamped industrial-depth (v388) proxies when that overlay is ON;
  otherwise documented geometry mass proxies with recorded source.
- Bookkeeping identity checks (direct sum, total identity, non-negativity) gate
  `costing_v421_consistency_ok`; informational cross-checks against the frozen legacy /
  component (v356) / industrial (v388) / availability-coupling (v420) CAPEX bases.
- LCOE restatement **only** on the availability-coupling (v420) energy/OPEX/replacement basis —
  when that overlay is OFF, `costing_v421_LCOE_USD_per_MWh` is NaN with an explicit basis note
  (no invented energy denominator).
- `costing_v421_LCOE_USD_per_MWh` registered in `plant_kpi_honesty.v1` LCOE aliases —
  hard-infeasible points display "— (diagnostic)", never a healthy LCOE.

### Wiring

- PointInputs flag + optional caps (`capex_total_max_MUSD_v421`,
  `lcoe_bottom_up_max_USD_per_MWh_v421`, `costing_consistency_tol_v421`).
- `hot_ion.py` post-process overlay after v420 (empty patch when OFF — no L0 / golden drift).
- Optional hard caps in `authority_caps.json` (+ regenerated codegen, 34 specs); user-facing
  cap names carry **no version tags** ("Total CAPEX cap", "Bottom-up LCOE cap").
- Run-artifact economics table exports v421 ledger keys when present.
- UI (all labels version-tag-free per the no-version-labels rule):
  Streamlit Systems panel (metrics + account ledger expander + honesty watermark),
  authority dashboard toggle, NiceGUI mission snapshot / control contracts / Suite authority
  ledger (account table with PROXY badges), Point Designer toggles/labels.

### Tests

- `tests/test_bottom_up_costing_authority_v421.py` (17 tests: account structure and identities,
  hand-checked accounts, v388 mass preference, provenance labels, informational cross-ledger
  checks, LCOE basis honesty, determinism, caps echo, UI helpers, flag-off L0 no-drift via
  Evaluator, honesty interplay, constraint registration with no-version-tag names).

### L0 risk

None — overlay only; flag OFF returns `{}`.
