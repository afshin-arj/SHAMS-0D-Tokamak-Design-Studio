# Patch Notes — v401.0.0

**Title:** Neutronics & Materials Authority 3.0 — Tiered Contract Governance  
**Author:** © 2026 Afshin Arjhangmehr

## What changed

This release adds a *governance-only* overlay that closes a key remaining physics-depth gap versus PROCESS-style studies: **explicit, tiered neutronics/materials contracts**.

v401 does **not** change the frozen truth evaluator and does **not** introduce any new solvers or hidden iteration.

## New capability

### 1) Contract tier overlay (v401)

- Adds `include_neutronics_materials_authority_v401` with tier selection:
  - **OPTIMISTIC** / **NOMINAL** / **ROBUST**
- Each tier defines deterministic screening limits over already-computed proxies:
  - TF-case fluence (from v392 or stack proxy)
  - Bioshield dose-rate proxy (v392)
  - TF nuclear heating (stack partition)
  - FW DPA rate (v390 or stack)
  - FW He total (stack)
  - Activation index (v390)
  - Minimum TBR (stack proxy)
- Computes:
  - per-item normalized margins
  - minimum margin and **dominant limiter**
  - fragility class (INFEASIBLE / FRAGILE / FEASIBLE / UNKNOWN)

### 2) UI integration

- New Point Designer expander: **🧾 Neutronics & Materials Contract Tiers — v401.0.0**
- Deep View: Neutronics & Nuclear Loads now shows v401 tier summary and a contract-item table when enabled.

## Determinism / audit

- Purely algebraic scoring; missing upstream quantities yield NaN margins and `UNKNOWN` classification.
- A fixed contract hash stamp is written to artifacts for traceability.
