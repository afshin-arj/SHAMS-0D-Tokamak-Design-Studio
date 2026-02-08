# SHAMS Reference Library (Read-only; validation only)

This folder contains literature-derived reference metadata and extracted values used **only** for validation and benchmarking.

## Design rules
- Read-only reference data (no runtime coupling to models)
- No PROCESS code/data/formats used at runtime
- Every extracted value is accompanied by provenance (paper id + notes)

## Contents
- `metadata/`: YAML files describing each reference (title, year, PDF hash, what was extracted)
- `data/`: extracted equations/scaling exponents (JSON/CSV)

## Running benchmarks
From repo root (after installing requirements):

```bash
python -m verification.run_physics_benchmarks
```

This writes `verification/physics_benchmark_report.json`.
