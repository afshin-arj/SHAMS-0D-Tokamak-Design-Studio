# Model Cards (Auditability)

SHAMS uses lightweight **model cards** to make every proxy model auditable and reproducible.

## Where they live
- YAML cards: `src/model_cards/*.yaml`
- Loader / index: `src/provenance/model_cards.py`

## What a model card contains
Typical fields:
- `id` (stable identifier, e.g. `engineering.radial_stack`)
- `version` (semantic version string)
- `module` and `entrypoint` (where the model is implemented)
- assumptions, validity range, and uncertainty notes

## How SHAMS uses them
At evaluation time, SHAMS emits a `model_cards` index in outputs:
- `id → {version, sha256, module, entrypoint}`

This index is intended to be written into run artifacts and into PDF/HTML reports, so decisions can be traced back to the exact model definitions used.

## Updating model cards
When you change a proxy in a decision-relevant way:
1. Update the model card version.
2. Ensure the model card text reflects the new assumptions/limits.
3. Add/adjust a requirement in `requirements/SHAMS_REQS.yaml`.
4. Run the verification harness.

