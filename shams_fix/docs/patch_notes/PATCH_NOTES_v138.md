# PATCH NOTES — v138 (2026-01-18)

This release includes v134–v138 as a single integrated upgrade, accessible in one unified UI.

v134 — FC Boundary Atlas
- tools.fc_advanced.build_fc_atlas_bundle: feasibility scatter + dominant constraint tables
- UI tab: build/download fc_atlas_v134.zip

v135 — Guided Completion
- tools.param_guidance: suggested FREE variables + suggested bounds + sanity warnings
- UI tab: Guided Setup

v136 — Bounded Feasibility Repair
- tools.fc_advanced.repair_to_feasibility: auditable hill-climb on worst_hard_margin_frac within bounds
- UI tab: Repair (requires non-feasible points retained)

v137 — Feasible Set Compression
- tools.fc_advanced.compress_feasible_set: top-K feasible representatives
- UI tab: Compress

v138 — FC → Study Handoff
- tools.fc_advanced.completion_to_run_artifact: evaluate a feasible completion as a new run_artifact
- UI tab: Handoff (creates a pinned run for v132 Study Matrix Builder)

Safety:
- No physics/solver/constraint logic changes. All additions are downstream orchestration/UI + new export bundles.
