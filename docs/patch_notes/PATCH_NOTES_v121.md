# PATCH NOTES — v121 (2026-01-17)

Mission Context Layer (L3) — advisory mission overlays (no physics/solver changes).

Added:
- missions/:
  - pilot.json
  - demo.json
  - powerplant.json
- schemas:
  - shams_mission_spec.schema.json
- tools:
  - tools.mission_context:
    - list_builtin_missions
    - load_mission
    - apply_mission_overlays -> shams_mission_report
    - mission_report_csv
  - tools.cli_mission_context
- UI:
  - Mission Context (v121) panel (replaces placeholder call; additive implementation)
  - layer registry updated to point to v121 panel
- Self-test:
  - generates mission_report_v121.json and mission_gaps_v121.csv

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior and workflows
