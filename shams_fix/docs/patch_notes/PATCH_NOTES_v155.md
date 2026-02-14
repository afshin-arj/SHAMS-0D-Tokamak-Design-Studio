# PATCH NOTES — v155 (2026-01-18)

Study Kit extensions (v153–v155) — single integrated upgrade

v153 DOI Export Helper
- tools.doi_export: zenodo_metadata_from_registry + crossref_minimal_from_registry
- UI + CLI exports (zenodo_metadata_v153.json, crossref_minimal_v153.json)

v154 Caption Editor
- UI caption editor storing caption overrides in session
- paper pack now embeds captions.json using overrides when provided

v155 Multi-Study Comparison Pack
- tools.multi_study_pack: bundle multiple paper packs + comparison report + integrity manifest
- UI uploader + exports, plus CLI

Safety:
- Downstream only; no physics/solver changes.
