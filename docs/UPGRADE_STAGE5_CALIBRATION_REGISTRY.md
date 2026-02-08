# Stage 5 — Calibration registry

Adds:
- `calibration/registry.py` with `CalibrationRegistry` + `CalibrationFactor`
- upgrades `apply_calibration()` to accept registry-like dicts
- evaluator now records the applied factors and registry metadata in outputs

Design intent: calibration is **transparent**, **versionable**, and **artifact-recorded**.
