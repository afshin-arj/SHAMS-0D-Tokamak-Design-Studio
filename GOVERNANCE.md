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

## Authority overlay catalog (v396–v408)

Additive governance modules post-process `hot_ion_point` outputs. None mutate L0 truth unless explicitly versioned (see `GOVERNANCE.md` change control).

| Version | Module | Default | Constraint ledger | Dedicated test |
|---------|--------|---------|-------------------|----------------|
| v396 | `analysis/transport_envelope_v396.py` | OFF | spread cap (optional) | yes |
| v397 | `src/analysis/profile_proxy_v397.py` | OFF | profile caps | yes |
| v398 | `src/analysis/control_stability_v398.py` | OFF | VS/RWM caps | yes |
| v399 | `src/physics/impurities/species_library_v399.py` | OFF | Zeff/Prad caps | yes |
| v400 | `src/analysis/magnet_technology_authority_v400.py` | **ON** | `constraints.py` caps | yes |
| v401 | `src/analysis/neutronics_materials_authority_v401.py` | OFF | nm fragile margin | yes |
| v402 | `src/analysis/authority_dominance_v402.py` | ON* | not wired | yes (isolated) |
| v403 | `src/analysis/neutronics_materials_library_v403.py` | OFF | nm v403 caps | yes |
| v404 | `src/analysis/structural_life_authority_v404.py` | OFF | `constraints.py` | yes |
| v406 | `src/extopt/frontier_intake_v406.py` | N/A | extopt intake | yes |
| v407 | `src/analysis/nuclear_data_authority_v407.py` | OFF | not wired | yes |
| v408 | `src/nuclear_data/intake.py` | N/A | tooling only | yes |

\* v402 schema default is ON but pipeline merge uses a relative import that can fail silently when `physics.hot_ion` is loaded as a top-level module; see audit PROPOSAL-007.

Canonical implementations live under `src/analysis/` with repo-root `analysis/` shims for legacy imports. Constraint wiring split: `constraints/system.py` (PROCESS ledger) vs `constraints/constraints.py` (runtime checks).
