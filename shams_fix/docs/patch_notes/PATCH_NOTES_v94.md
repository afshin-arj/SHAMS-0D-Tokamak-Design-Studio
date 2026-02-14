# PATCH NOTES — v94 (2026-01-08)

Unified Export Bundle + Run Records (additive).

Added:
- Unified export bundle builder: `tools/export/bundle.py` (zip of artifacts + capsule + schemas + figures pack).
- UI: "Unified Export Bundle (v94)" panel in Point Designer (build/download one zip).
- UI: "Run Records" tab (session timeline; rerun-safe).
- State: `run_history` list initialized lazily.

Unchanged:
- Physics
- Solvers
- Defaults
