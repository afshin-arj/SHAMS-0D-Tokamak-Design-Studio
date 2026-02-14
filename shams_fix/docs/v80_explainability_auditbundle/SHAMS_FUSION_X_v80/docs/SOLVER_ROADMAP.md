# SHAMS–FUSION-X Solver Roadmap (Long-Term, Academic-Grade)

**Scope:** This roadmap is *interface- and evidence-focused*. It does **not** prescribe physics changes or solver behavior changes.
SHAMS mainline remains **constraint-first, audit-ready, continuation-centric, and deterministic by default**.

## Immutable principles
1. **Feasibility is primary.** Infeasibility is a valid result (never silently coerced).
2. **Continuation over iteration.** Continuation is the default narrative for families of solutions.
3. **Diagnostics over speed.** Convergence without explanation is insufficient.
4. **Deterministic replay.** Results must be reproducible with explicit provenance.
5. **Backend pluralism.** Multiple backends may be supported, but must not change scientific meaning.

## Roadmap axes (orthogonal)
### A. Continuation intelligence (annotations only)
- Adaptive step sizing with recorded rationale
- Boundary proximity metrics (distance-to-violation scalars)
- Detection/classification of folds/termination causes

### B. Solver backend pluralism (workflow primitive)
- Deterministic Newton continuation (baseline)
- Trust-region variants (bounded, conservative)
- Interval/box feasibility solvers (certificate-grade)
- Surrogate assistance for *post-analysis only* (never authoritative solve)

### C. Failure-mode taxonomy (publishable)
- Formalize non-solution classes: infeasible / inconsistent / degenerate / terminated
- Solver-independent failure codes and statistics across scans
- “Why did this fail?” narratives tied to constraint ledgers and margins

### D. Reproducibility science
- Run manifests with hashes (inputs, constraints, solver backend, environment)
- Deterministic cache lineage and replay scripts
- Artifact schemas versioned and documented

## Deliverable policy
Roadmap items land in mainline only if they are:
- **Purely additive**
- **Opt-in**
- **Zero-risk to physics/solver behavior**
- **Audit-traceable**
