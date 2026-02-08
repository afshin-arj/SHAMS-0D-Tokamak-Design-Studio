# PATCH NOTES — v113 (2026-01-16)

Design Decision Layer (DDL) — additive decision support (no optimization).

Added:
- tools.design_decision_layer:
  - build_design_candidates: creates shams_design_candidate objects from feasible artifacts
  - build_design_decision_pack: exports candidates + comparison CSV + report + manifest as a zip
- tools.cli_design_decision_pack:
  - builds decision pack offline from artifacts + optional topology/component/boundary/family/overlay inputs
- UI (Run Ledger): Design Decision Layer (v113)
  - builds candidates and offers one-click download of design_decision_pack.zip

Self-test:
- tools.ui_self_test now also produces:
  - design_decision_pack.zip
  - design_candidates.json
  - design_decision_manifest.json
  - audit pack includes a summary record of the decision pack

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
