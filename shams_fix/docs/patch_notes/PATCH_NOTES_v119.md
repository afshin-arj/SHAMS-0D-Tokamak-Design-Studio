# PATCH NOTES — v119 (2026-01-16)

Authority Pack — journal / GitHub / regulator-ready publishable evidence bundle.

Added:
- schemas:
  - shams_authority_pack_manifest.schema.json
- tools.authority_pack:
  - build_authority_pack: zips VERSION, patch notes, requirements_freeze (best-effort), command log, methods appendix, selected artifacts, and integrity manifest
- tools.cli_authority_pack:
  - offline builder (optionally include audit pack / downstream bundle / handoff pack)
- UI:
  - Authority Pack (v119) panel
    - builds a single authority_pack_v119.zip with manifest
- Self-test:
  - generates authority_pack_v119.zip and authority_pack_manifest_v119.json (best-effort)
  - audit summary includes authority pack reference via generated files

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
