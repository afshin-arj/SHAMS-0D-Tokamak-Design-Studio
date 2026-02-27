# PATCH NOTES — v406.0.0
Author: © 2026 Afshin Arjhangmehr

## Upgrade: External Optimizer Interpretation Layer — Frontier Intake (Firewalled)

### What shipped
- **v406 Frontier Intake**: ingest external optimizer candidate sets (**CSV or JSON**), plus a **base_inputs.json**, then:
  - deterministically re-evaluate every candidate through frozen truth,
  - evaluate **optimistic vs robust** UQ-lite lanes (deterministic interval corners),
  - detect **mirage** candidates (optimistic pass, robust fail),
  - reconstruct feasible-only **Pareto fronts** (optimistic-front and robust-front) under user-declared objectives.

### Hard guarantees preserved
- No truth mutation.
- No internal optimization.
- Deterministic, replayable artifacts; stable hashing.

### UI
- Added **“🧭 Frontier Intake (v406)”** tab in **External Optimizer Suite**.

### Examples
- New folder: `examples/extopt_frontier_intake_v406/` with:
  - `base_inputs_sparc_like.json`
  - `candidate_set_example.csv` / `candidate_set_example.json`
  - `objectives_example.json`
  - `optimistic_uncertainty_spec.json` / `robust_uncertainty_spec.json`
