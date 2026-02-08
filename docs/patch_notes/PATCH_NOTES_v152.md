# PATCH NOTES — v152 (2026-01-18)

Result Integrity Lock in UI (v152)

Added:
- tools.run_integrity_lock: lock_run + verify_run (SHA256 over canonical JSON serialization)
- tools.cli_run_integrity_lock
- UI: Run Integrity Lock panel with download + Vault save

Behavior:
- Shows UNLOCKED / VERIFIED / MODIFIED status per run (based on stored lock in session)
- Downstream-only: does not alter physics/solver behavior.

Notes:
- Locks are stored in session_state (and optionally exported to Vault). Import/restore can be added later.
