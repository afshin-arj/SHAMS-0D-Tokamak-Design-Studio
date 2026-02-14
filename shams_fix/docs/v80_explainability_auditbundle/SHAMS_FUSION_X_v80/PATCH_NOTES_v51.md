# PATCH_NOTES_v51 — UI surfacing

This patch adds three Streamlit UI tabs:

- **Artifacts Explorer**: load `shams_run_artifact.json` and view `constraint_ledger`, `model_set`/`model_registry`, and standardized `tables`.
- **Case Deck Runner**: upload a case deck YAML/JSON and run it from the UI (writes outputs under `ui_runs/`).
- **Scenario Delta Viewer**: upload baseline + scenario artifacts and view embedded `scenario_delta` when present, otherwise a computed transparent diff of inputs and numeric outputs.
