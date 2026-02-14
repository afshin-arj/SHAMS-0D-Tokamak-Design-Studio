# PATCH NOTES — v120 (2026-01-17)

Constitutional Release — layered architecture, governance, and UI layer registry.

Added:
- Constitutional docs:
  - ARCHITECTURE.md
  - GOVERNANCE.md
  - LAYER_MODEL.md
  - NON_OPTIMIZER_MANIFESTO.md
  - CITATION.cff
- UI:
  - Constitution & Layer Registry panel
  - Placeholders for Mission Context and Explainability layers (schema-first roadmap)
  - ui/layer_registry.py (layer entries for higher layers)
- tools:
  - tools.constitution.build_constitution_manifest (SHA256 integrity manifest)
- schemas:
  - shams_constitution_manifest.schema.json

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior and workflows (additive panels only)
