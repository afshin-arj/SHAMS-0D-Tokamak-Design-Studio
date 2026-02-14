# PATCH NOTES — v167 (2026-01-18)

Design Study Authority Pack

Adds v167 one-click bundle for publishable design studies:
- tools.authority_pack_v167: build_authority_pack() -> zip bytes + manifest
- tools.cli_authority_pack_v167 writes authority_pack_v167.zip
- UI panel integrated after v166, before v160
- ui_self_test produces authority_pack_v167.zip + authority_pack_manifest_v167.json

Safety:
- Packaging only; no physics or solver logic changes.
