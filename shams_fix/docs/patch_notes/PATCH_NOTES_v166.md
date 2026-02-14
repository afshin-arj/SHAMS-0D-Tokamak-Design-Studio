# PATCH NOTES — v166 (2026-01-18)

Reproducibility Lock + Replay Checker

Adds v166 reproducibility lockfile and replay verification:
- tools.repro_lock_v166: build_repro_lock() and replay_check()
- tools.cli_repro_lock_v166
- UI panel integrated after v165, before v160
- ui_self_test produces repro_lock_v166.json and replay_report_v166.json

Safety:
- Evaluation-only; uses existing evaluator and compares outputs within tolerances.
- No physics or solver logic changes.
