# PATCH_NOTES_v24

This release adds the next project-grade upgrades on top of v23:

## 1) Proxy model cards (auditability)
- Added `src/model_cards/*.yaml` model cards for the main proxy stack.
- Added `src/provenance/model_cards.py` to load and hash cards.
- Evaluator now injects a compact `model_cards` index into outputs, and artifacts store it at top-level.

## 2) Radial stack minimum thickness constraints + ledger
- `constraints/system.py` now:
  - treats boolean feasibility keys (`radial_build_ok`, `stack_ok`, `LH_ok`) as real constraints (value must be 1.0)
  - adds min-thickness constraints automatically when `radial_stack` is present and a region declares `min_thickness_m > 0`
- UI `Checks & explain` now renders a `Radial stack (inboard)` table and margin summary when available.

Backward compatibility preserved:
- Existing artifacts and presets remain readable.
- If `radial_stack` is absent in older runs, min-thickness constraints are simply skipped.
