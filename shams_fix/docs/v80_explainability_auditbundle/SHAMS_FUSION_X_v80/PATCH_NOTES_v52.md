# PATCH_NOTES_v52.md

UI-first sprint (no physics changes).

Added four new Streamlit tabs:
- Run Library: scan a workspace folder for run artifacts and study indexes; open into session.
- Constraint Cockpit: interactive constraint-ledger triage with filters and top blocker view.
- Sensitivity Explorer: local finite-difference sensitivities around the loaded point (uses existing evaluator; read-only).
- Feasibility Map: 2D heatmap viewer for study sweeps (study_index.v1), with per-cell case loading.

All changes are additive and backward-compatible. No existing artifact schema keys were removed or renamed.
