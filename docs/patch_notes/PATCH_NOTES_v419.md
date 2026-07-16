# PATCH NOTES — v419.0.0

## v419.0.0 — Plant Sankey-grade ledger authority (Independence Phase 2.3)

Author: © 2026 Afshin Arjhangmehr

### MATCH-as-overlay

- New authority: `plant_sankey_ledger_authority_v419` (`include_plant_sankey_ledger_authority_v419`, OFF by default).
- Extends v408 CD-mix plant ledger + L0 `plant_power_closure` with explicit source→sink flows:
  fusion → α / neutrons → radiation / divertor → blanket thermal → gross electric →
  recirculating (HCD, cryo, pumping, tritium plant, BOP, TF ohmic) → net electric.
- Conservation residual checks (plasma power, electric identity, recirc component sum).
- PROXY provenance; no invented PROCESS MFILE numbers.
- Pe_net display still gated by `plant_kpi_honesty.v1` watermark.

### Wiring

- PointInputs flags + optional caps (`plant_sankey_f_recirc_max_v419`, `plant_sankey_Pe_net_min_MW_v419`, `P_tritium_plant_MW`).
- `hot_ion.py` post-process overlay (empty patch when OFF — no L0 / golden drift).
- Soft conservation + optional hard caps in `constraints.py` / `authority_caps.json`.
- `shams_io/sankey.py` prefers stamped v419 kwargs when enabled.
- UI: Streamlit PD magnet/plant panel, NiceGUI mission snapshot / control contracts / Suite authority ledger, authority dashboard toggle.

### Tests

- `tests/test_plant_sankey_ledger_authority_v419.py`

### L0 risk

None — overlay only; flag OFF returns `{}`.
