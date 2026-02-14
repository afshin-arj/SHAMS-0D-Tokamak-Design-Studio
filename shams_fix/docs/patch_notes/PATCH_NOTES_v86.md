# PATCH NOTES — v86 (2026-01-08)

v86 adds **External Proposer Mode** to the SAFE Optimization Sandbox.

## Added
- CLI: `python -m tools.sandbox.external_proposer`
  - Audits external candidate designs via SHAMS (feasibility gate)
  - Keeps only audited-feasible candidates
  - Optionally merges with an existing SHAMS feasible dataset
  - Ranks merged pool using explicit objectives (non-authoritative ranking layer)

- UI: External Proposer section inside Optimization Sandbox tab
  - Upload candidates JSON (PROCESS or other)
  - SHAMS audits candidates and ranks audited-feasible designs

## Unchanged
- Physics models
- Solver logic / continuation behavior
- Constraint definitions and enforcement
- Defaults

## Safety invariants preserved
- One-way dependency (sandbox consumes SHAMS truth)
- No penalty-based relaxation
- Explicit non-authoritative labeling
