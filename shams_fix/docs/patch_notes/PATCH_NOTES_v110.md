# PATCH NOTES — v110 (2026-01-16)

Feasibility Boundary Atlas v2 (additive).

Added:
- tools.boundary_atlas_v2:
  - build_boundary_atlas_v2: extracts explicit boundary polylines between feasible/infeasible samples for lever-pair slices
  - best-effort boundary labeling using failure taxonomy modes
- tools.plot_boundary_atlas_v2:
  - plots boundary polylines to PNG/SVG (matplotlib defaults)
- UI (Run Ledger): Boundary Atlas v2 (v110) panel
  - build and export boundary_atlas_v2.json
- tools.ui_self_test now also produces:
  - boundary_atlas_v2.json
  - boundary_plots/*.png|svg
  - audit pack includes atlas v2 artifact

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
