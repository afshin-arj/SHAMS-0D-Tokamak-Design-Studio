# PATCH NOTES — v103 (2026-01-16)

Consolidated upgrades v100–v103 (additive only):

v100 Audit Pack
- tools.audit_pack.build_audit_pack_zip
- UI panel: Audit Pack zip builder

v101 Constraint Explainability 2.0 (safe form)
- Uses frontier-based nearest-feasible sweeps as repair guidance (no physics changes)

v102 Feasibility Boundary Atlas
- tools.frontier_atlas.build_feasibility_atlas
- UI panel: build/download atlas, records to Run Ledger

v103 Optimizer Sandbox Plus
- tools.sandbox_plus.run_sandbox wraps existing optimize_design (random/LHS)
- UI panel: run/download sandbox_plus, records to Run Ledger

Unchanged:
- Physics
- Solvers defaults
- Core behavior
