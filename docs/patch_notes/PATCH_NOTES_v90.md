# PATCH NOTES — v90 (2026-01-08)

Reproducibility + offline verification release (additive).

Added:
- Reproducibility Capsule exporter: `python -m tools.export.capsule --artifact-json ... --outdir ...`
- UI: Export capsule from cached Point Designer artifact (downloads capsule.zip)
- JSON schemas in `schemas/` for core artifacts (run artifact, feasible set, PROCESS handoff)
- Offline verification tool: `python -m tools.verify_package [--emit-dummy-capsule]`
- UI session state model stub (`ui/state.py`) for future refactor

Unchanged:
- Physics
- Solvers
- Defaults
- Constraint logic
