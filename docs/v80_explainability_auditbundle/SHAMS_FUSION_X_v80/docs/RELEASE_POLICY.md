# Release Policy

## Naming
All deliverables are distributed as **versioned, date-tagged zip files**:
- `SHAMS_FUSION_X_v{major}_{tag}_2026-01-08.zip`

## Semantic intent
- Major (v80, v81, …): additive capability that does **not** change physics/solver behavior.
- Patch/UI/tooling: additive only; defaults remain unchanged.

## Allowed changes in mainline releases
- Documentation
- Audit artifacts (manifests, ledgers, certificates)
- UI read-only panels or opt-in exports
- Telemetry extensions that do not affect solve order or convergence

## Disallowed in mainline without explicit request
- Physics model changes
- Solver algorithm changes
- Default parameter changes
- Performance “optimizations” that change execution ordering or numerical outcomes

## Required artifacts
Each release includes:
- VERSION marker
- Release notes
- Governance + release policy
- Reproducibility notes (how to regenerate key results)
