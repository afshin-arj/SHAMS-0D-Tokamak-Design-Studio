# Availability 2.0 — Reliability Envelope Authority (v391.0.0)

This example demonstrates enabling the **v391 availability reliability envelope** (governance-only).

Key points:

- Deterministic and algebraic (no RAMI simulation).
- Uses MTBF/MTTR proxies per subsystem class:
  - `A_i = MTBF / (MTBF + MTTR)`
  - `A_unplanned = Π A_i`
- Applies explicit **planned outage** (`planned_outage_days_per_y_v391 / 365`).
- Applies **maintenance downtime** informed by:
  - v368/v359 replacement/outage fraction (if enabled)
  - v390 cooldown and maintenance burden factor (if enabled)

Outputs to inspect:

- `availability_cert_v391`
- `planned_outage_frac_v391`
- `maint_downtime_frac_v391`
- `unplanned_downtime_frac_v391`
- `availability_ledger_v391`

## How to run

1. Launch SHAMS UI.
2. Go to **🧭 Point Designer → Engineering & plant feasibility**.
3. Enable **🧩 Availability & reliability envelope (v391.0.0)**.
4. (Optional) Enable v368 and/or v390 to see maintenance/cooldown coupling.
5. Run Point evaluation and open **🧪 Telemetry → Fuel Cycle · Lifetime · Availability**.
