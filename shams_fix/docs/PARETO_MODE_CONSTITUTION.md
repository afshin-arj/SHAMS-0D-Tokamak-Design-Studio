# Pareto Mode Constitution (0-D, Feasible-Only, Non-Optimizing)

**Component:** Pareto Mode  
**System:** SHAMS / Tokamak 0-D Design Studio  
**Author:** © 2026 Afshin Arjhangmehr

## 1. Role

Pareto Mode is a **trade-off cartography instrument** operating strictly on the **feasible design set** as defined by the frozen Point Designer evaluator (and intent-aware constraint policy).

It answers:

- What trade-offs are **unavoidable**?
- Which constraints **pin** each segment of the Pareto front?
- Where is **freedom left** (flat trade-offs)?
- How **fragile** is a compromise under uncertainty/robustness lenses?

## 2. Authority and Truth Flow

- **Point Designer defines truth.**
- **Systems Mode negotiates feasibility recovery around that truth.**
- **Scan Lab reveals why truth has its structure.**
- **Pareto Mode reveals trade-offs within the feasible truth.**

Pareto Mode **must not** create feasibility and **must not** reinterpret evaluator outcomes.

## 3. Explicit Non-Goals (Permanent)

Pareto Mode will never:
- Optimize, solve, or recommend a “best design”
- Relax constraints or modify constraint policy
- Hide infeasibility or smooth evaluator discontinuities
- Introduce weighted-objective sliders that imply a single optimum
- Auto-select “knees” as recommendations

## 4. Frozen Semantics

The following are part of Pareto Mode meaning:
- **Feasibility gate:** Pareto is computed on feasible points only.
- **Objective contract:** Objectives are explicit (name, direction, units, source).
- **Front annotation:** Dominant constraint and minimum margin are attached to points/segments.
- **Robustness lenses:** Any robust overlay is labeled as a lens, not a solver.
- **Geography metaphors:** “ridge/cliff/plain” are descriptive summaries of constraint/topology behavior.

## 5. Reproducibility Requirements

A Pareto run must be:
- Deterministic under fixed seed / sampling configuration
- Replayable from an exported artifact
- Audit-ready with evaluator/policy hashes and objective contract preserved

## 6. Post-Freeze Change Policy

After Pareto v1.0 freeze, allowed changes are:
- Documentation / teaching materials
- UI clarity that does not alter semantics
- Bug fixes that preserve behavior and determinism
- Performance improvements that do not change results
- Backward-compatible artifact readers/upgraders

Any change affecting semantics, determinism, or artifact meaning requires a new major version.

