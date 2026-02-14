# SHAMS–FUSION-X Governance & Release Policy (v120)

## Scope
This document defines rules for changes to SHAMS to ensure journal / GitHub / regulator readiness.

## Change Control
### Frozen by default
- **No physics, constraint, solver logic, or behavior changes** unless explicitly requested and versioned.
- Additive changes (UI panels, exporters, schemas, documentation) are permitted.

### Release discipline
- Releases are **versioned + date-tagged** zip files.
- Every release includes:
  - VERSION
  - patch notes
  - self-test updates (where applicable)
  - schemas/manifests for new artifacts

### Compatibility
- Backward-compatible additions are preferred.
- Breaking changes require a major version note and migration instructions.

## Auditability requirements
- Every exported bundle must include a manifest with SHA256 hashes.
- Workflows must be reproducible offline (no internet required).

## Scientific integrity
- SHAMS must avoid hidden objectives or black-box selection.
- Preference scoring is annotation-only; SHAMS does not perform embedded optimization.


## Policy Contracts (Feasibility Semantics)

SHAMS supports **explicit, reviewer-visible policy tiering** for selected operational limits (e.g. q95, Greenwald fraction).
This is a *semantics* layer only:

- Physics outputs are unchanged.
- Constraints are still computed and reported.
- Enforcement tier may be downgraded **HARD → SOFT** when policy specifies `diagnostic`.

### Current supported policy toggles (v232)
- `q95_enforcement`: `hard | diagnostic`
- `greenwald_enforcement`: `hard | diagnostic`

### Auditability
- Policy is stamped into outputs as `outputs["_policy_contract"]`.
- Constraints affected by policy carry `provenance.policy_override`.
- UI always shows policy status in Systems Mode when any gate is downgraded.

This preserves the “frozen truth evaluator” while permitting explicit exploration of speculative/advanced regimes.
