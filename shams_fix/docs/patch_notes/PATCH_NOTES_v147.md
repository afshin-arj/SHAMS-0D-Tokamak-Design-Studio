# PATCH NOTES — v147 (2026-01-18)

Feasibility completion (single integrated upgrade v146–v147)

v146 — Feasibility Bridge Certificate
- tools.feasibility_bridge.run_bridge: continuation-style witness path between two points
- tools.feasibility_bridge.bridge_certificate: citable summary + hashes
- UI: Bridge Certificate panel (select Point A/B from run history)

v147 — Guaranteed Safe Domain Shrink
- tools.safe_domain_shrink.run_safe_domain_shrink: shrink-to-certify loop using v144 interval certification
- UI: Safe Domain Shrink panel producing safe interval box + evidence report

Safety:
- Downstream only; no physics/solver changes.
