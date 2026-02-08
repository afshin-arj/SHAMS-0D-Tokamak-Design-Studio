# PATCH NOTES — v160 (2026-01-18)

Design Space Authority: v156 + v160 (single upgrade)

v156 Feasibility Field Engine
- tools.feasibility_field: build_feasibility_field() outputs shams_feasibility_field (v156) + csv + atlas zip
- tools.cli_feasibility_field

v160 Feasibility Authority Certificates
- tools.feasibility_authority_certificate: issue_certificate_from_field() issues shams_feasibility_authority_certificate (v160)
- tools.cli_feasibility_authority_certificate
- UI panels integrated under Study Kit: Feasibility Atlas (v156) and Authority Certificate (v160)

Safety
- Downstream-only: uses existing point evaluator + constraints; no physics/solver changes.
- All features remain accessible through the single integrated UI.
