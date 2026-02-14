# PATCH NOTES — v324.0

## Design Family Narratives & Regime Maps

This upgrade implements the next locked roadmap item: **v324 — Design Family Narratives & Regime Maps**.

### What’s new

- **Trade Study Studio → 🗺️ Regime Maps & Narratives (v324)**
  - Deterministic clustering of **feasible** designs into families.
  - Regime labeling driven by the **closest-to-violation (dominant) constraint**, enriched via `constraints.taxonomy`.
  - Per-family narrative synthesis:
    - feature ranges (min/median/max)
    - margin statistics
    - authority metadata (subsystem, tier, validity-domain string)
  - Exportable, reviewer-ready artifact: `regime_maps_report.json`.

### Determinism & safety

- No truth changes: frozen evaluator untouched.
- No internal optimization.
- No solver iteration: clustering uses quantized bins + deterministic merging.

Author: © 2026 Afshin Arjhangmehr
