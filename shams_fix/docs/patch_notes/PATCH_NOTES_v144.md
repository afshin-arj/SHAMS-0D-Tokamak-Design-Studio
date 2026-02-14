# PATCH NOTES — v144 (2026-01-18)

Feasibility Deep Dive (single integrated upgrade v142–v144)

v142 — Feasible Topology Maps
- tools.feasibility_deepdive.sample_and_evaluate: bounded sampling + feasibility evaluation
- tools.feasibility_deepdive.topology_from_dataset: kNN graph components (feasible islands)
- Bundle: topology_bundle_v142.zip

v143 — Constraint Interaction Graphs
- tools.feasibility_deepdive.interactions_from_dataset: dominance + co-failure matrix (top constraints)
- Bundle: interactions_bundle_v143.zip

v144 — Interval Feasibility Certificates
- tools.feasibility_deepdive.interval_certificate: corner checks + random interior probes (conservative)
- Bundle: interval_bundle_v144.zip

UI:
- New single panel with tabs v142–v144, integrated into the unified UI.
- Vault export for each bundle.

Safety:
- Downstream only; no physics/solver changes.
