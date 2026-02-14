# PATCH NOTES — v116 (2026-01-16)

Design Study Kit: Design Handoff Pack (engineering-ready, publishable export).

Added:
- schemas:
  - shams_handoff_pack_manifest.schema.json
- tools.handoff_pack:
  - build_handoff_pack: exports a handoff_pack.zip from a run artifact
  - includes: artifact json, inputs yaml, constraints csv, summary, README, figures, manifest (SHA256)
- tools.cli_handoff_pack:
  - builds handoff pack offline from a saved run artifact JSON
- UI:
  - Design Handoff Pack (v116) panel
    - select any run artifact from ledger (defaults to last pinned)
    - build and download handoff_pack.zip + manifest
- Self-test:
  - generates handoff_pack.zip and handoff_pack_manifest.json
  - audit pack includes handoff pack summary

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
