# Release notes generation

SHAMS includes a lightweight release-notes generator that summarizes:
- **Structural changes** (constraints set/meta changes, model card hash/version changes, schema_version changes)
- **Benchmark numeric deltas** that exceed tolerances (from `benchmarks/last_diff_report.json`)

## Typical workflow

1. In the *new* version repo, run benchmarks:

```bash
python benchmarks/run.py --write-diff
```

2. Generate markdown release notes comparing two repos:

```bash
python tools/release_notes.py --old ..\SHAMS_old --new . --out RELEASE_NOTES.md
```

## Notes

- Structural diffs use the full golden artifacts under `benchmarks/golden_artifacts/`.
- Numeric diffs use the diff report JSON, if available.
