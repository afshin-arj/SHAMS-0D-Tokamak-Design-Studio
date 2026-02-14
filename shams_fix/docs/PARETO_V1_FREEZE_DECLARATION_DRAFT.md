# Pareto Lab v1.0 — Freeze Declaration (Draft)

**Component:** Pareto Lab  
**System:** SHAMS / Tokamak 0-D Design Studio  
**Author:** © 2026 Afshin Arjhangmehr

## Role

Pareto Lab maps unavoidable trade-offs among **feasible** 0-D designs under an explicit
Design Intent and constraint policy. It is an interpretability instrument for trade-offs,
not a generator of designs.

## Non-Goals (Permanent)

Pareto Lab will never:
- Optimize or search for designs
- Relax constraints or modify evaluator policy
- Recommend choices or select “best” points
- Hide fragility or imply certainty without evidence
- Create feasibility that does not exist

## Frozen Semantics

The following are frozen as part of meaning:
- “Feasible-only” gate and intent-aware hard constraints
- Definition of dominance / non-dominated set
- Segment explanation semantics (what pins a trade-off)
- Confidence and incompleteness signals (sampling-based, explicitly labeled)
- Narrative templates are descriptive and conditional
- Artifact schema v1 and replay semantics

## Allowed Post-Freeze Changes

- Documentation and teaching material
- UI clarity that does not alter semantics
- Bug/performance fixes that preserve determinism and meaning
- Backward-compatible artifact readers/upgraders

Any change to interpretation, determinism, or evaluator interaction requires a new major version.

## Declaration

**Pareto Lab v1.0 is hereby declared freeze-ready** once golden fronts and regression guards
are finalized for the canonical objective templates.
