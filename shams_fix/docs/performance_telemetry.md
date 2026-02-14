# Performance Telemetry
**Author:** Afshin Arjhangmehr  
**Date:** 2026-01-08

Metrics:
- wall_s: wall-clock time
- eval_sum_s: sum of per-task eval times
- speedup_est = eval_sum_s / wall_s
- throughput

Outputs:
- Scan: <out>_stats.json
- Benchmarks: <out>_perf_stats.json
- Pareto: result['perf']
