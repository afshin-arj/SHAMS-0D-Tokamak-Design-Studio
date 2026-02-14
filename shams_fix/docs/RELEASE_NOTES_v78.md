# SHAMS–FUSION-X v78 Release Notes (Publishable)
**Author:** Afshin Arjhangmehr  
**Release date:** 2026-01-08

## Overview
v78 adds **performance telemetry** for opt-in parallel runs and caching, without altering physics or default solver behavior.

## Additions
- Scan runs now emit `<out>_stats.json` containing wall-time, eval-time sum, and speedup estimates.
- Pareto optimizer returns a `perf` block with wall-time and estimated speedup when parallel is enabled.
- Benchmark runner emits `<out>_perf_stats.json` and includes per-case `eval_s` in results.

## Guarantees
- Results are unchanged; telemetry is derived only from timers.
- Ordering is preserved in parallel execution.
