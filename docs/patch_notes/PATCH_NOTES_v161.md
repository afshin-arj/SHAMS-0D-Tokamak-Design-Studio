# PATCH NOTES — v161 (2026-01-18)

Completion Frontier + Minimal Change Distance

Adds v161 completion frontier analysis for partial designs:
- tools.completion_frontier: build_completion_frontier()
- tools.cli_completion_frontier
- UI panel: Completion Frontier (v161) integrated after v159, before v160
- ui_self_test produces completion_frontier_v161.json

Safety:
- Downstream-only sampling search using existing evaluator + constraints; no physics or solver logic changes.
