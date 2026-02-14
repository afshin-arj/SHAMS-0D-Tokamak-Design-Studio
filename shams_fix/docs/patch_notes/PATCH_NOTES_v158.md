# PATCH NOTES — v158 (2026-01-18)

Constraint Dominance Topology (Design Space Authority)

Adds v158 dominance + topology from v156 feasibility fields:
- tools.constraint_dominance: build_constraint_dominance()
- tools.cli_constraint_dominance
- UI panel: Constraint Dominance Topology (v158) integrated after v157, before v160
- ui_self_test produces constraint_dominance_v158.json

Safety:
- Downstream-only analysis of stored margins/labels; no physics or solver logic changes.
