# Structural diff severity and PDF changelog

SHAMS produces two kinds of regression information:

1. **Numeric diffs**: key KPIs compared against `benchmarks/golden.json` with tolerances.
2. **Structural diffs**: changes in constraint definitions and model card identities.

## Severity classification

Structural diffs are classified as:

- **info**: bookkeeping changes, low impact
- **warn**: likely behavior change
- **breaking**: likely to break downstream assumptions or feasibility expectations

Heuristics (transparent, deterministic):

- Constraint removed → **breaking**
- New **hard** constraint added → **breaking**
- New **soft** constraint added → **warn**
- Constraint rename → **breaking** (detected as remove+add with identical meta)
- Constraint sense/limit change → **breaking**
- Model card hash/version change → **warn**
- Model card change **while out-of-validity** for the evaluated point → **breaking**

The per-case details are written into:

- `benchmarks/last_diff_report.json` → `structural_severity`

## PDF changelog section

Every summary PDF includes a **Changelog (code)** page section:
- SHAMS version + schema version
- Embedded verification requirement pass/fail summary (if present)
- `RELEASE_NOTES.md` excerpt (if present)

This keeps decision PDFs self-contained and auditable.
