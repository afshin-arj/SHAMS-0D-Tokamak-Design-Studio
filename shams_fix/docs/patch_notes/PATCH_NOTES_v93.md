# PATCH NOTES — v93 (2026-01-08)

UI state-machine expansion + auto-validation + paper figures pack (additive).

Added:
- Paper figures pack builder (`tools/paper_figures_pack.py`) + Point Designer UI panel to build/download `paper_figures_pack.zip`.
- Stateful Systems/Scan/Sandbox panels with schema checks (where applicable) and downloads sourced from session state.
- Auto-validation helper `_v93_validate_before_download` (jsonschema if available; fallback otherwise).

Unchanged:
- Physics
- Solvers
- Defaults
