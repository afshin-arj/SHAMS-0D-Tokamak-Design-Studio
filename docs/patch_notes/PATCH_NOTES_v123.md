# PATCH NOTES — v123 (2026-01-17)

Evidence Graph + Traceability (v123) and Design Study Kit (v123B).

Added:
- schemas:
  - shams_evidence_graph.schema.json
  - shams_traceability_table.schema.json
  - shams_design_study_kit_manifest.schema.json
- tools:
  - tools.evidence_graph:
    - build_evidence_graph
    - build_traceability_table
    - traceability_csv
  - tools.study_kit:
    - build_study_kit_zip (manifested publishable bundle)
  - CLI:
    - tools.cli_evidence_graph
    - tools.cli_study_kit
- UI:
  - Evidence Graph & Design Study Kit (v123 / v123B) panel
  - layer registry includes this utility panel entry
  - removed duplicate placeholder calls (mission/explainability placeholders) so single UI stays clean
- Self-test:
  - generates evidence_graph_v123.json, traceability outputs, and study_kit_v123B.zip

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior and workflows (additive panels only)
