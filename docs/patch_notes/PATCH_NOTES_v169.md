# PATCH NOTES — v169 (2026-01-18)

Feasibility Boundary Atlas (Publishable Figure Pack)

Adds v169 atlas pack generator:
- tools.atlas_v169: build_atlas_pack() -> atlas_pack_v169.zip + manifest
- tools.cli_atlas_v169
- UI panel integrated after v164, before v165
- ui_self_test produces atlas_pack_v169.zip + atlas_manifest_v169.json

Notes:
- v169 uses v164 sensitivity as a fast "local atlas" around a witness (offline-friendly).
- Captions are embedded per-page in JSON to prevent mixed-caption PNG exports.
