# PATCH_NOTES_v29

## Added: Golden artifacts + tolerance diff regression

### Benchmarks
- `benchmarks/golden_artifacts/` contains full run artifacts for each benchmark case.
- `benchmarks/update_golden_artifacts.py` regenerates:
  - `benchmarks/golden.json` (curated numeric metrics)
  - `benchmarks/golden_artifacts/*.json` (full artifacts)

### Diff report
- `benchmarks/run.py` now writes `benchmarks/last_diff_report.json` (machine-readable).
- UI Benchmarks tab shows the latest diff report and writes it after each run.

### Robustness fix
- `src/shams_io/run_artifact.py` now accepts constraints in both schemas:
  - legacy PROCESS-like (`sense/limit/passed`)
  - SHAMS bounded form (`lo/hi`)
  It normalizes before summarization/serialization so artifact creation is reliable.

### Docs
- Added `docs/REGRESSION.md` and linked from UI Docs.

### Tests
- Added `tests/test_benchmarks_diff_report.py` to ensure diff report is produced.
