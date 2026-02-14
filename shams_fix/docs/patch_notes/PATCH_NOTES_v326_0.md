# PATCH NOTES — v326.0

Author: © 2026 Afshin Arjhangmehr

## v326.0 — UI Interoperability Contract Validator

This release adds a deterministic, reviewer-safe validator for SHAMS UI wiring
and cross-panel interoperability **without executing physics, solvers, or optimization**.

### Added
- **Control Room → Interoperability contract validator (v326)**
  - Static discovery of subpanel functions in `ui/app.py` (no import execution).
  - Validation of declared `ui.panel_contracts` coverage against discovered subpanels.
  - Contract sanity checks (empty `requires`, duplicate required keys).
  - Optional runtime presence check for declared required `st.session_state` keys.
  - JSON report rendered in an expander.

### New modules
- `tools/interoperability/contract_validator.py`

### Tests
- `tests/test_contract_validator.py` (determinism + smoke)

### Non-changes (by design)
- No modifications to frozen truth / evaluator.
- No changes to physics closures, constraints, or authority math.
- No changes to any optimizer, certified search, or external kit behavior.
