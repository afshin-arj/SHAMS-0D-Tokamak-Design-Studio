# PATCH NOTES — v26

This release adds **compliance surfacing** (requirements + model cards) in the UI and embeds the latest
verification report into run artifacts for auditability.

## Added
- UI tab **Compliance**:
  - Reads `verification/report.json`
  - Shows PASS/FAIL summary + detailed requirements table
  - Allows downloading the JSON report
- Docs:
  - `docs/COMPLIANCE.md`

## Artifact provenance
- `src/shams_io/run_artifact.py` now attaches the latest `verification/report.json` (if present) into the
  run artifact under `artifact["verification"]`:
  - `report` (full JSON)
  - `report_hash` (SHA256)

If `verification/report.json` is not present, artifacts remain unchanged.

## How to generate verification/report.json
From repo root:

```bash
python verification/run_verification.py
```
