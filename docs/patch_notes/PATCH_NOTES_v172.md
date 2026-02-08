# PATCH NOTES — v172 (2026-01-18)

Demo artifact seed + panel hydration

Adds v172 demo seeding:
- tools.demo_seed_v172: build_demo_bundle(), install_demo_bundle(session_state)
- tools.cli_demo_seed_v172
- UI: "Demo seed (v172)" in More tab to load/clear synthetic demo artifacts for offline panel hydration

Notes:
- Demo artifacts are explicitly non-authoritative and marked as synthetic.
- No physics/solver behavior changes.
