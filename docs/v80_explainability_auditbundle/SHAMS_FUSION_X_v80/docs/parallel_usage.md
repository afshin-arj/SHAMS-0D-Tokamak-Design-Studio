# Parallel Execution (v77)
**Author:** Afshin Arjhangmehr  
**Date:** 2026-01-08

Parallelism is **opt-in** and preserves ordering.

## Scan runs
```bash
python tools/studies/scan.py --base <base.json> --var <field> --lo <x> --hi <y> --n 51 --parallel --workers 4
```

## Pareto sampling
- Programmatic:
```python
from solvers.optimize import pareto_optimize
res = pareto_optimize(base, bounds, objectives, n_samples=400, parallel=True, workers=4)
```
- Or via environment (keeps UI call sites unchanged):
```bash
set SHAMS_PARALLEL_PARETO=1
set SHAMS_WORKERS=4
```

## Benchmarks
```bash
python benchmarks/run.py --parallel --workers 4
```
