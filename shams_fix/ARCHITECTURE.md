# SHAMS–FUSION-X Architecture (Constitutional Release v120)

This release establishes SHAMS as a **layered, constraint-first, audit-ready design authority system**.

## Core Principle
**L0 (Frozen Core)** produces validated run artifacts from explicit inputs using deterministic physics + constraints.
All higher layers are **read-only consumers** of L0 artifacts and may only:
- derive annotations,
- generate reports,
- build export bundles,
- append to the run ledger (never mutate prior artifacts).

## Layer Model
SHAMS layers are orthogonal and optional:
- **L0** — Frozen Physics + Constraints (authority anchor)
- **L1** — Authority & Reference (governance, citation, versioning, reproducibility)
- **L2** — Engineering Interfaces (export adapters; downstream tools consume SHAMS)
- **L3** — Mission Context (scenario definitions; no new physics)
- **L4** — Explainability (narratives, causal summaries; no ML required)

## UI Contract
One Streamlit UI (`ui/app.py`) provides access to all layers as **panels**.
Panels must not:
- change physics, constraints, or solver behavior,
- silently “optimize” or auto-select a best design,
- overwrite user results or clear session state during downloads.

## Artifact Contract
Artifacts are immutable once written. Any new processing produces a new artifact and a new manifest with hashes.

## External Optimizers
External optimizers are treated as **proposal generators only**.
SHAMS remains the authority by re-evaluating proposals using frozen physics + constraints and exporting evidence.

