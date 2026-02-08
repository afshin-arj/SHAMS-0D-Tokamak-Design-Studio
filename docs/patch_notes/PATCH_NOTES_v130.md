# PATCH NOTES — v130 (2026-01-17)

Persistent Run Vault (storage-only).

Added:
- tools:
  - tools.run_vault: append-only vault writer + index
  - tools.cli_run_vault
- UI:
  - Persistent Run Vault panel (v130)
- Integration:
  - _v98_record_run now (optionally) persists payloads to the vault (never blocks UI)

Safety:
- Vault writes are best-effort and wrapped; failures never affect UI execution.
- No changes to physics/constraints/solvers.

Vault:
- out_run_vault/INDEX.jsonl + entries/...
