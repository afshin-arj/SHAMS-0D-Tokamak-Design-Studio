# Benchmarks and Physics Reports

SHAMS includes a lightweight regression harness to protect physics and solver behavior from unintended changes.

## Run

From repo root:

```bash
python benchmarks/run.py
```

To intentionally update golden numbers (only when you have explicitly requested behavior changes):

```bash
python benchmarks/run.py --generate
```

## Outputs

- `benchmarks/golden.json`  
  Curated regression numbers for a small set of cases in `benchmarks/cases.json`.

- `benchmarks/last_diff_report.json` (only when failures occur)  
  Human-readable diff report for curated keys.

- `benchmarks/last_physics_report.json` (always best-effort, never gates)  
  A wider set of physics/audit outputs (alpha/ash, power-channel bookkeeping, radiation breakdown, particle diagnostics).  
  This report is for inspection and provenance only; it does not affect pass/fail.

## Adding a new benchmark case

1. Add an entry to `benchmarks/cases.json` with overrides that match fields in `PointInputs`.
2. Regenerate golden numbers intentionally:

```bash
python benchmarks/run.py --generate
```

3. Commit both `cases.json` and `golden.json`.

SHAMS philosophy note: benchmarks are *feasibility-first*; no case should silently mask non-feasibility.
