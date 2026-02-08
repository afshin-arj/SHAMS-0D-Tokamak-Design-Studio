# PATCH NOTES — v108 (2026-01-16)

Interoperability Dominance: Make PROCESS downstream (additive).

Added:
- tools.process_downstream:
  - build_process_downstream_bundle: exports a PROCESS-like CSV table from SHAMS run artifacts
- tools.cli_process_downstream:
  - offline builder from run artifact JSON files
- UI (Run Ledger): PROCESS Downstream Export panel:
  - select run artifacts → generate bundle zip and download
- tools.ui_self_test now also produces:
  - process_downstream_bundle.zip
  - process_downstream_manifest.json
  - audit pack includes downstream summary

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
