# PATCH NOTES — v170 (2026-01-18)

PROCESS Downstream Export (Interoperability Dominance)

Adds v170 export pack generator:
- tools.process_export_v170: build_process_export_pack() -> process_export_pack_v170.zip + manifest
- tools.cli_process_export_v170
- UI panel integrated after v168, before v160
- ui_self_test produces process_export_pack_v170.zip + process_export_manifest_v170.json

Notes:
- This is an interoperability shim. It exports PROCESS-like CSV tables and a conservative alias mapping.
- No PROCESS physics is reimplemented; SHAMS remains upstream authority.
