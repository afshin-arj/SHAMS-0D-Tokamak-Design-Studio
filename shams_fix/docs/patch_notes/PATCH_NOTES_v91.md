# PATCH NOTES — v91 (2026-01-08)

Offline-verifiable quality release (additive).

Added:
- Schema validator: `python -m tools.validate_schemas --json ... --schema ...`
- Figure export utilities: `src/shams_io/figure_export.py`
- Dual-export radial build helper: `plot_radial_build_dual_export(...)` (PNG + SVG best-effort)
- Offline figure verification: `python -m tools.verify_figures`
- UI state model integration (incremental): session_state now initializes `SessionStateModel` and mirrors cached Point Designer results there.

Unchanged:
- Physics
- Solvers
- Defaults
- Constraint logic
