# PATCH NOTES — v105 (2026-01-16)

Direction B — Pillar 2: Constraint Dominance & Sensitivity (additive).

Added:
- tools.constraint_dominance:
  - build_constraint_dominance_report (failure + near-boundary ranking)
  - extract_constraint_rows_from_payload (run artifact extractor)
- UI (Run Ledger): Constraint Dominance panel:
  - builds report from selected run artifacts (default pinned)
  - records to Run Ledger, downloadable JSON
- tools.ui_self_test now also produces:
  - constraint_dominance_report.json (built from deterministic sample artifacts)
  - confidence report includes its hash/size

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
