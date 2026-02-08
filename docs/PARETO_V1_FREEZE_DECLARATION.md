# Pareto Mode v1.0 — Freeze Declaration

**Component:** Pareto Mode  
**System:** SHAMS / Tokamak 0‑D Design Studio  
**Version:** v1.0 (Frozen at v196.1, 2026-01-26)  
**Author:** © 2026 Afshin Arjhangmehr

## Role
Pareto Mode is a **descriptive, feasibility‑preserving instrument** for revealing unavoidable trade‑offs among explicit objectives in the 0‑D tokamak design space.

It operates exclusively on designs deemed **feasible** by the frozen Point Designer evaluator (intent-aware) and does not create, relax, or recommend designs.

## Authority Boundaries
- **Point Designer defines truth.**
- **Systems Mode negotiates feasibility around that truth.**
- **Pareto Mode maps trade‑offs within feasible truth.**

Pareto Mode does not override or reinterpret evaluator outcomes.

## Permanent Non‑Goals
Pareto Mode will never:
- Optimize or search for “best” designs
- Relax constraints or modify policies
- Rank, score, or recommend designs
- Hide fragility, infeasibility, confidence limits, or uncertainty
- Substitute interpretability with automation

## Frozen Semantics (Normative)
The following meanings are frozen:
- **Pareto optimality**: non‑dominated **among feasible designs** under the frozen evaluator, declared objectives, and declared intent
- **Objective contract**: explicit min/max sense, units, and evaluator-sourced fields (no hidden objectives)
- **Constraint dominance / first‑failure**: how segments are annotated and interpreted
- **Robustness / fragility / confidence**: definitions, labels, and thresholds used for presentation (no silent drift)
- **Narrative language**: descriptive, conditional, non‑prescriptive wording
- **Visual semantics**: ordering, badges, and color meaning
- **Determinism and replay**: same inputs → same artifact and same front (within stated sampling contract)
- **Artifact schema v1**: structure and replay semantics

## Allowed Post‑Freeze Changes
Permitted without a new major version:
- Documentation and teaching materials
- UI clarity/accessibility improvements **without semantic change**
- Bug fixes preserving determinism and meaning
- Performance improvements **without result changes**
- Backward‑compatible artifact readers/upgraders

## Major Version Triggers
Any change affecting:
- Interpretation of trade‑offs or segment meaning
- Definition of feasibility/dominance/robustness/confidence
- Determinism or reproducibility guarantees
- Objective semantics or policy interaction
requires a new major version.

## Declaration
**Pareto Mode v1.0 is hereby declared frozen.**  
It exists to **explain trade‑offs**, not to decide them.
