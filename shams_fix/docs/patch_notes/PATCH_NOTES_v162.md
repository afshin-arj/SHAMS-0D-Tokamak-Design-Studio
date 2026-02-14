# PATCH NOTES — v162 (2026-01-18)

Directed Local Search (Safe)

Adds v162 directed local search from a baseline guess:
- tools.directed_local_search: build_directed_local_search()
- tools.cli_directed_local_search
- UI panel: Directed Local Search (v162) integrated after v161, before v160
- ui_self_test produces directed_local_search_v162.json

Safety:
- Downstream-only coordinate hill-climb with strict evaluation budget + bounded variables.
- No physics or solver logic changes.
