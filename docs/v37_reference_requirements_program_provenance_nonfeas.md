# SHAMS v37 Upgrade: Reference Design + Requirements + Program Risk + Provenance + Non-Feasibility

This release strengthens SHAMS as a **decision-authoritative** system tool while preserving:
- transparent proxies
- feasibility-first
- artifact-driven reproducibility
- Windows-native Python-only operation

## Added capabilities

### 1) Reference design synthesis
Study outputs (`studies/runner.py`) now include a `reference_design` block in `index.json`.
Selection is **transparent** and based on:
- hard feasibility
- decision-grade maturity (unless waived)
- weighted regret over COE / net power / robustness / margins

Implementation: `src/decision/reference_design.py`

### 2) Requirements satisfaction matrix
If `requirements/requirements.yaml` exists, each run artifact embeds:
- `requirements_trace.overall` and per-req status/evidence.

Implementation: `src/decision/requirements_trace.py`

### 3) Time-explicit program risk envelope
Each run artifact embeds a lightweight schedule proxy:
- build_years
- commission_years
- outage_days_per_year
- delivery_risk_proxy

Implementation: `src/program/risk.py`

### 4) Constraint provenance fingerprints
Each constraint JSON entry now includes:
- `provenance.constraint_fingerprint_sha256`

This fingerprint is the SHA256 of a stable subset of constraint-defining fields.

### 5) Explicit non-feasibility certificates
If hard infeasible, artifacts include:
- `nonfeasibility_certificate` with dominant blockers and best knob suggestions.

PDF front page includes a short excerpt.

## Notes
- All additions are **additive** (backward compatible). Older artifacts still load.
- All logic is transparent and editable (no black boxes).
