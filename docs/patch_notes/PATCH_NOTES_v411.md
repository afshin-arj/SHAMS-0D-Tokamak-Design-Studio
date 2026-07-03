# PATCH NOTES — v411.0.0

## v411.0.0 — PROPOSAL-007: v402 dominance pipeline import (governance)

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-007 — Authority Dominance Engine 2.0 pipeline merge

- `src/physics/hot_ion.py`: flat `from analysis.authority_dominance_v402` import fallback before relative import, matching v367/v400 overlay wiring.
- Schema default `include_authority_dominance_v402=True` now produces dominance keys in standard `hot_ion_point` evaluation path.
- **Governance-only:** no change to frozen physics scalars (Pin, Pfus, W, τE, etc.); additive v402 output keys only.

### Tests

- `tests/test_v402_pipeline_hot_ion.py` — E2E regression pin for default-ON v402 merge.

### Regenerated baselines

- `tests/golden/*.json` (10 cases) — v402 dominance keys added to canonical outputs.

### Expected deltas

- New keys per case: `dominance_order_v402`, `global_dominant_authority_v402`, `global_min_margin_v402`, `mirage_flag_v402`, `mirage_reasons_v402`, `regime_class_v402`, `dominance_gap_to_second_v402`, `include_authority_dominance_v402=True`.

No intentional change to power balance, confinement, or constraint physics.
