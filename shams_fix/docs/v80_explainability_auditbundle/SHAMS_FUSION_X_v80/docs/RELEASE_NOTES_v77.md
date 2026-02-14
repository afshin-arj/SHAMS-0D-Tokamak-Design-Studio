# SHAMS–FUSION-X v77 Release Notes (Publishable)
**Author:** Afshin Arjhangmehr  
**Release date:** 2026-01-08

## Overview
v77 is a performance-focused release providing **opt-in** speed improvements while preserving physics and default solver behavior.

## Additions
- Evaluation caching with explicit cache hit/miss/eviction stats.
- Solver backend option: `hybrid_newton` (default) and `broyden` (opt-in) with explicit trace logging.
- Parallel execution options (opt-in, order-preserving):
  - Scan runs (`tools/studies/scan.py --parallel`)
  - Pareto sampling (`src/solvers/optimize.pareto_optimize(parallel=True)`)
  - Benchmark harness (`benchmarks/run.py --parallel`)

## Non-changes
- Physics models unchanged.
- Default solver behavior unchanged.
- No silent feasibility logic changes.
