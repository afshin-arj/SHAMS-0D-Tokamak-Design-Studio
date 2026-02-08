# PATCH NOTES — v133 (2026-01-18)

Feasibility Completion Engine (Partial Design Inference).

Added:
- tools:
  - tools.feasibility_completion: FCConfig + feasibility completion search (grid/random) + fc bundle zip
  - tools.cli_feasibility_completion
- UI:
  - Feasibility Completion panel (v133) integrated into the single unified UI
  - Optional: save FC bundle to vault with attachments

Safety:
- No physics/solver changes. FC is orchestration only and uses existing evaluator.

Outputs:
- fc_report_v133.json
- fc_bundle_v133.zip (report + csv + manifest)
