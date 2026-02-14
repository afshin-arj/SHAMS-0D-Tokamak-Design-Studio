# Compliance & Verification

SHAMS uses a **requirements-first** verification harness to prevent regressions and to make runs **auditable**.

## What runs in verification

The verification runner (`verification/run_verification.py`) executes:

- Benchmarks / golden cases (deterministic checks)
- Requirement acceptance checks declared in `requirements/SHAMS_REQS.yaml`
- Provenance checks (e.g., model card IDs present in outputs)

It writes a single machine-readable file:

- `verification/report.json`

## Where the report is used

### UI
The Streamlit UI includes a **Compliance** tab that loads `verification/report.json` and shows:

- Overall PASS/FAIL summary
- A requirements table (ID, status, details)
- Download button for the JSON report

### Run artifacts
When a run artifact is built (`src/shams_io/run_artifact.py`), SHAMS will attempt to attach the
latest `verification/report.json` (if present) under:

- `artifact["verification"]["report"]`
- `artifact["verification"]["report_hash"]`

This makes every artifact self-contained for audits.

## How to generate the report

From the repo root:

```bash
python verification/run_verification.py
```

Or via tests:

```bash
pytest
```

Tip (Windows): use the same environment you run SHAMS with, so the report captures correct Python/package versions.
