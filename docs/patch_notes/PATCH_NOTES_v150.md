# PATCH NOTES — v150 (2026-01-18)

Design Study Authority (one big jump v148–v150)

v148 — Paper Pack Generator
- tools.design_study_kit.build_paper_pack: exports zip with artifacts/certificates/figures/tables
- Adds reproduce scripts + environment snapshot

v149 — Study Registry (DOI-ready metadata)
- tools.design_study_kit.build_study_registry + schema

v150 — Result Integrity Lock
- tools.design_study_kit.build_integrity_manifest + verify helper
- Embedded integrity_manifest_v150.json in every paper pack

UI:
- New Publishable Study Kit panel in integrated UI, with Vault export.

Safety:
- Downstream only; no physics/solver changes.
