# PATCH NOTES — v124 (2026-01-17)

Feasibility Boundary Atlas (SHAMS-native advantage).

Added:
- schemas:
  - shams_feasibility_atlas.schema.json
- tools:
  - tools.feasibility_atlas:
    - available_numeric_levers
    - scan_grid (frozen physics + constraints)
    - build_feasibility_atlas_bundle (boundary extraction + plots + manifest + zip)
  - tools.cli_feasibility_atlas
- UI:
  - Feasibility Boundary Atlas (v124) panel (single UI, additive)
  - layer registry includes v124 panel entry
- Self-test:
  - builds small 9x9 atlas and stores atlas_bundle_v124.zip + feasibility_atlas_v124.json

Unchanged:
- Physics and constraints logic
- Solvers and behavior
