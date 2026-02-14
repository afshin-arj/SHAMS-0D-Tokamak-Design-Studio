# PATCH NOTES — v157 (2026-01-18)

Feasibility Boundary Extractor (Design Space Authority)

Adds v157 boundary extraction from v156 feasibility fields:
- tools.feasibility_boundary: build_feasibility_boundary()
- tools.cli_feasibility_boundary
- UI panel: Feasibility Boundary (v157) integrated between v156 and v160 panels
- ui_self_test produces feasibility_boundary_v157.json

Safety:
- Downstream-only extraction from stored margins; no physics or solver logic changes.
