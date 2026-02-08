# PATCH NOTES — v139 (2026-01-18)

v139 — Feasibility Certificates (journal/regulator-ready)

Additions
- tools.feasibility_certificate.generate_feasibility_certificate(...):
  - emits an immutable certificate JSON for any shams_run_artifact
  - includes full hard-constraint table, dominance ordering, solver context, and reproducibility hashes
  - includes SHAMS version and a best-effort code hash derived from repo provenance
- UI: new integrated layer panel “Feasibility Certificate (v139)”
  - select any run from the ledger
  - generate certificate
  - download JSON or save to Vault
- tools.ui_self_test now generates feasibility_certificate_v139.json for regression coverage

Safety
- No physics, solver logic, or constraint behavior changes.
- Certificates are downstream artifacts derived from existing run artifacts.
