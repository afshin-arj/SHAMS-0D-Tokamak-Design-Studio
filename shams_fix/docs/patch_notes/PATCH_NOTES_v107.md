# PATCH NOTES — v107 (2026-01-16)

Direction B — Feasibility Science Pack (capstone; additive).

Added:
- tools.science_pack:
  - build_feasibility_science_pack: combines topology + dominance + failures
  - produces:
    - feasibility_science_pack.zip
    - FEASIBILITY_SCIENCE_REPORT.md (inside zip)
    - feasibility_science_pack_summary.json
    - science_pack_manifest.json
- tools.cli_science_pack:
  - offline builder from three JSON artifacts
- UI (Run Ledger): Feasibility Science Pack panel
  - one-click pack build and zip download
- tools.ui_self_test now also produces:
  - feasibility_science_pack.zip
  - feasibility_science_pack_summary.json
  - science_pack_manifest.json
  - confidence report includes their hash/size

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
