# PATCH NOTES — v92 (2026-01-08)

UI state-machine + offline validation + plot-layout testing (additive).

Added:
- UI state-machine helpers (_v92_state_get, _v92_state_clear_point) and a persistent "Stateful Results" panel in Point Designer.
- UI schema validation panel (More tab): upload any JSON artifact and validate against shipped schemas (offline-friendly).
- Deterministic plot layout test: `python -m tools.tests.test_plot_layout` (exercise radial-build export repeatedly).
- Expanded SessionStateModel fields (point/systems/scan/sandbox) for future full refactor.

Unchanged:
- Physics
- Solvers
- Defaults
