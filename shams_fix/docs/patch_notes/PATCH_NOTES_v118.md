# PATCH NOTES — v118 (2026-01-16)

Optimizer Downstream Workflow — external optimizers propose; SHAMS validates, envelopes, decides.

Added:
- schemas:
  - shams_optimizer_batch_response.schema.json
- tools.optimizer_downstream:
  - template_batch_response
  - evaluate_optimizer_batch:
    - v115 evaluate proposals -> run artifacts
    - filter feasible
    - v117 tolerance envelopes for feasible candidates
    - v113 build candidates
    - v114 preferences + Pareto
    - v113 pack export with v118 justification
  - build_downstream_report_zip:
    - exports optimizer_downstream_bundle_v118.zip (report JSON + decision pack zip + manifest)
- tools.cli_optimizer_downstream:
  - offline v118 runner, writes templates + bundles
- UI:
  - Optimizer Downstream Workflow (v118) panel
    - upload optimizer batch json
    - uses current v114 prefs and v117 tolerance spec if available
    - outputs report JSON, decision pack v118, and downstream bundle zip
- Self-test:
  - generates downstream report, decision pack v118, downstream bundle zip + manifest
  - audit pack includes downstream summary

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
