# PATCH NOTES — v104 (2026-01-16)

Direction B — Pillar 1: Feasible Space Topology (additive).

Added:
- tools.topology:
  - build_feasible_topology (graph + connected components)
  - extract_feasible_points_from_payload (Scan/Atlas/Sandbox/run artifacts)
- UI (Run Ledger): Feasible Space Topology panel:
  - build topology from selected runs (default pinned)
  - records topology artifact to Run Ledger
- tools.ui_self_test now also produces:
  - feasible_topology.json
  - confidence report includes its hash/size

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
