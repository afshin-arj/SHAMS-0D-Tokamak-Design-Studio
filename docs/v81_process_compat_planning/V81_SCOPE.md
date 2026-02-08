# v81 Scope — Feasible Design Space Characterization

v81 introduces formal, first-class treatment of feasible design spaces.
No physics, solver logic, or defaults are modified.

## Core Additions
- Formal definition of Feasible Scans
- Feasible/infeasible tagging for all scan points
- Constraint margin vectors and active constraint IDs
- Failure-mode classification for infeasible points

## Intended Outcome
SHAMS becomes the authoritative generator of feasible design sets
for downstream optimization tools (e.g., PROCESS).
