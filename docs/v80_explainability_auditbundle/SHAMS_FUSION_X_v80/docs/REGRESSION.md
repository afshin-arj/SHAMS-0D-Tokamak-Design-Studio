# Regression benchmarks & golden artifacts

SHAMS ships with a small regression suite under `benchmarks/` to catch unintended changes in proxy models,
constraints, solvers, and economics.

## What runs

- `benchmarks/cases.json` defines a small set of SPARC-like cases (baseline + targeted variations).
- `benchmarks/run.py` evaluates each case and compares a curated set of outputs to `benchmarks/golden.json`.

## Golden references

There are two complementary golden references:

### 1) Curated numeric keys (fast)
`benchmarks/golden.json`

A compact JSON mapping `{case -> {metric -> value}}` used by the default benchmark runner.

### 2) Golden run artifacts (audit-friendly)
`benchmarks/golden_artifacts/*.json`

Full schema-versioned run artifacts for each benchmark case. These are helpful when you want to:
- inspect which constraint flipped,
- see margin changes,
- confirm model card provenance.

To regenerate both:
```bash
python benchmarks/update_golden_artifacts.py
```

## Diff reports

Both the CLI and UI write a machine-readable diff report:

`benchmarks/last_diff_report.json`

This is used by CI and by the Streamlit Benchmarks tab.

## Recommended workflow

- For day-to-day development: run
```bash
python benchmarks/run.py
```

- When you deliberately change physics proxies or constraints:
  1) run the suite,
  2) review diffs,
  3) regenerate golden references only after review:
```bash
python benchmarks/update_golden_artifacts.py
```


## Structural diffs

When benchmarks are run with `--write-diff`, SHAMS also records structural diffs vs the golden artifacts (constraint set/meta and model cards) into `benchmarks/last_diff_report.json`.
