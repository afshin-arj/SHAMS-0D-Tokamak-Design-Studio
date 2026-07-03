# PATCH NOTES — v414.0.0

## v414.0.0 — Top-5 audit findings (PROPOSAL-010–012 + certification)

Author: © 2026 Afshin Arjhangmehr

### PROPOSAL-010 — Constraint pipeline sync

- `constraints/system.py`: mirror v396/v397/v384/v407 caps in PROCESS ledger.
- `constraints/constraints.py`: v407 fluence cap in governance path.

### PROPOSAL-011 — Overlay failure surfacing

- `hot_ion.py`: `_record_overlay_failure()` for v401/v403/v404/v407/v402/v372 overlays with `*_error` keys.

### PROPOSAL-012 — Import fallbacks

- `hot_ion.py`: dual import paths for v401/v403/v404, bootstrap/NI/neutronics-materials blocks.
- `certification/impurity_radiation_detachment_certification_v380.py`: physics import fallback.

### AUD-012 — Certification coverage

- `tests/test_top5_audit_fixes.py`: import smoke for all 16 certification modules.

### Golden

Regenerated `tests/golden/*.json` — additive v401/v403 keys from fixed overlay imports; no physics equation changes.
