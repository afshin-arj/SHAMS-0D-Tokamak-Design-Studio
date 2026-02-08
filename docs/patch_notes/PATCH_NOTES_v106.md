# PATCH NOTES — v106 (2026-01-16)

Direction B — Pillar 3: Failure Mode Taxonomy (additive).

Added:
- tools.failure_taxonomy:
  - build_failure_taxonomy_report (dominant-failing constraint classification + aggregates)
  - extract_failure_record (from run artifacts)
- UI (Run Ledger): Failure Mode Taxonomy panel:
  - builds taxonomy from selected run artifacts (default pinned)
  - records to Run Ledger, downloadable JSON
- tools.ui_self_test now also produces:
  - failure_taxonomy_report.json
  - confidence report includes its hash/size
  - audit pack includes taxonomy artifact

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
