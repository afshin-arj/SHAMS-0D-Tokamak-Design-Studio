# PATCH NOTES — v159 (2026-01-18)

Feasibility Completion Evidence (Design Space Authority)

Adds v159 completion evidence for partial designs:
- tools.feasibility_completion_evidence: build_feasibility_completion_evidence()
- tools.cli_feasibility_completion_evidence
- UI panel: Feasibility Completion Evidence (v159) integrated after v158, before v160
- ui_self_test produces feasibility_completion_evidence_v159.json

Safety:
- Downstream-only sampling search using existing evaluator + constraints; no physics or solver logic changes.
