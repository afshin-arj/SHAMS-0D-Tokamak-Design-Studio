# Nuclear Datasets (External Intake) — v408

This directory holds *externally imported* nuclear screening datasets used by the
v407/v408 Nuclear Data Authority pipeline.

## Hard rules (SHAMS frozen truth discipline)

- These datasets are used only for **deterministic algebraic screening proxies**.
- No Monte Carlo.
- No transport solvers.
- No spectral iteration.
- Every dataset must include explicit provenance fields and is pinned by
  **SHA-256** of the canonical JSON payload.

## File conventions

- `*.json` — dataset payload (schema-compatible with `NuclearDataset`)
- `*.md` — optional human-readable evidence card (recommended)

## Intake pathways

1) Streamlit UI panel: **Nuclear Dataset Intake & Provenance Builder (v408)**
2) CLI:

```bash
python tools/nuclear_dataset_intake_cli.py --json path/to/dataset.json
```

The evaluator will automatically list and load datasets found here.

Author: © 2026 Afshin Arjhangmehr
