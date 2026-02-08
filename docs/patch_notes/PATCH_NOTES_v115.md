# PATCH NOTES — v115 (2026-01-16)

External Optimizer Interface (EOI) — SHAMS remains authority; optimizers are downstream.

Added:
- schemas:
  - shams_optimizer_request.schema.json
  - shams_optimizer_response.schema.json
- tools.optimizer_interface:
  - template_request / template_response
  - evaluate_optimizer_proposal: re-evaluates proposed inputs with frozen physics+constraints
  - build_optimizer_import_pack: zips templates + evaluated artifact + import context
- tools.cli_optimizer_import:
  - write templates and evaluate proposal JSON offline
- UI:
  - External Optimizer Sandbox (v115):
    - download templates
    - upload optimizer_response JSON
    - evaluate proposal in SHAMS and record to run ledger
    - download optimizer_import_pack.zip

Self-test:
- generates optimizer templates, evaluated artifact, import context, and optimizer_import_pack.zip
- audit pack includes optimizer import summary

Unchanged:
- Physics
- Solvers defaults
- Existing UI behavior
