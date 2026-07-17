# PROCESS parity contribution process

**Independence Phase 4.3.** Labs that hold a licensed PROCESS installation (or permission to share extracts) can contribute reference cases so SHAMS can attach honest delta dossiers — **NUMERIC** when real MFILE/OUT.DAT KPIs are supplied, otherwise **METHOD-ONLY**.

**Related:** `docs/INDEPENDENCE_EXIT_EVIDENCE.md`, `docs/PROCESS_RETIREMENT_REPORT.md`, `docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`, `benchmarks/parity/process_reference_cases.json`.

## What you get back

1. A hashed **SHAMS delta dossier** (`shams_delta_dossier.v1`) with SHAMS verdict, KPIs, blockers, and (if NUMERIC) KPI deltas vs your PROCESS extract.
2. A **contribution receipt** (`shams.parity_contribution_receipt.v1`) with `dossier_sha256` and honesty flags.
3. Clear refusal if you request NUMERIC without real KPIs / provenance / license attestation — SHAMS will not invent MFILE numbers.

## Submission schema

Schema id: `shams.parity_contribution.v1`

| Field | Required | Notes |
|-------|----------|-------|
| `schema` | yes | Must be `shams.parity_contribution.v1` |
| `case_id` | yes | `^[a-z][a-z0-9_]{2,63}$` |
| `label` | yes | Human title |
| `requested_status` | yes | `METHOD-ONLY` or `NUMERIC` |
| `inputs` | yes | Non-empty PointInputs-compatible object |
| `process_reference` | yes | Object; KPIs null under METHOD-ONLY |
| `provenance` | yes | Source metadata |
| `license_attestation` | yes | License / share permission |
| `intent` | optional | e.g. `reactor` / `research` |
| `honesty.no_invented_mfile` | recommended | Must be true for NUMERIC |

Template: `benchmarks/parity/contributions/submission_template.json`

## Honesty rules

| Status | PROCESS KPIs | Provenance | License attestation |
|--------|--------------|------------|---------------------|
| **METHOD-ONLY** | All null / absent | Reason why no MFILE | May be false |
| **NUMERIC** | ≥1 real KPI | `process_reference_source` required | Must affirm license + share permission |

**Forbidden:** requesting NUMERIC with fabricated KPIs, inventing MFILE numbers, or claiming PROCESS retired because a dossier was accepted.

## How to contribute (CLI)

From `SHAMS-0D/`:

```powershell
# 1. Copy and edit the template (keep METHOD-ONLY until you attach real extracts)
Copy-Item benchmarks\parity\contributions\submission_template.json my_lab_case.json

# 2. Validate + build dossier (writes outbox receipt + dossier)
python -c "from pathlib import Path; from src.parity_harness.contribution import load_submission, process_contribution; r=process_contribution(load_submission(Path('my_lab_case.json'))); print(r['accepted'], r.get('dossier_sha256'), r.get('issues'))"
```

Or via the parity harness CLI:

```powershell
python -m src.parity_harness.cli contribute --submission my_lab_case.json --out_dir benchmarks/parity/contributions/outbox
```

Outbox paths (gitignored contents except template):

- `benchmarks/parity/contributions/outbox/<case_id>_delta_dossier.json`
- `benchmarks/parity/contributions/outbox/<case_id>_receipt.json`

## Promotion into the in-repo corpus

Accepted outbox dossiers are **not** automatically merged into `benchmarks/parity/process_reference_cases.json`. Maintainers promote after license review:

1. Confirm NUMERIC provenance + checksum of the lab extract (kept out of public git if license requires).
2. Add a corpus case with `dossier_status` matching the receipt.
3. Run `refresh_corpus_hashes` / corpus lock tests.
4. Never upgrade METHOD-ONLY → NUMERIC without real KPIs.

## What this does *not* mean

- It does **not** retire PROCESS.
- It does **not** claim community adoption.
- Scientific release remains **CONDITIONAL** until APPROVED evidence exists.
- Cite SHAMS with `VERSION` + dossier / artifact SHA-256; see `docs/CITE_SHAMS_HANDOFF.md`.

## Implementation

| Piece | Path |
|-------|------|
| Intake + validation | `src/parity_harness/contribution.py` |
| Delta dossier builder | `src/parity_harness/delta_dossier.py` |
| Corpus honesty | `src/parity_harness/process_corpus.py` |
| Lock tests | `tests/test_parity_contribution_and_exit_evidence.py` |
| Exit evidence | `docs/INDEPENDENCE_EXIT_EVIDENCE.md` |
