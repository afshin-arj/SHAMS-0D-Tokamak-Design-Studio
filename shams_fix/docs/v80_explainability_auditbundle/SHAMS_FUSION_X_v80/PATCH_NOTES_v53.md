# PATCH_NOTES_v53 — UI Upgrade Pack (no physics changes)

This patch adds nine **UI-only** upgrades (PROCESS-inspired decision workflow), without changing physics models or run artifacts.

## Added UI pages / capabilities
1. Decision Front Page Builder (reconstructs decision-grade summary from artifact)
2. Constraint Provenance Drill-Down (raw constraint + fingerprint metadata)
3. Knob Trade-Space Explorer (2-knob grid feasibility explorer)
4. Regression Viewer (“what broke?” across two artifacts)
5. Study Dashboard (headline + blocker distributions from study_index.v1)
6. Engineering Maturity Heatmap (model_registry/model_set visualization)
7. Assumption Toggle Bar (quick scenario toggles + reevaluation)
8. Export / Communication Panel (JSON/CSV/one-slide PNG summary)
9. Solver Introspection (trace / clamp / residual fields)

## Backward compatibility
- All changes are additive and confined to `ui/app.py` and patch notes.
- No model, constraint, or solver behavior is altered.

