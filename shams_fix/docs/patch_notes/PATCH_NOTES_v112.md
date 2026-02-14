# PATCH NOTES — v112 (2026-01-16)

Literature Overlay layer (additive; user-supplied).

Added:
- tools.literature_overlay:
  - template_payload + lightweight validation
  - extract_xy_points for plotting overlays on lever-pair slices
- tools.plot_boundary_overlay:
  - generates PNG/SVG per boundary slice with overlay points
- UI (Run Ledger): Literature Overlay (v112)
  - download template JSON
  - upload user-provided literature points JSON
  - preview overlay-able lever pairs

Self-test:
- tools.ui_self_test now produces:
  - literature_points_template.json
  - literature_points_baseline.json (internal self-test point; NOT literature)
  - boundary_overlay_plots/* (best-effort)
  - audit pack includes overlay payload

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
