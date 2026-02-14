# Studies (PROCESS-like workflows)

SHAMS supports program-grade studies that mirror how systems engineers use PROCESS.

## Scan study
Vary 1 knob across a range and record feasibility and objectives.

CLI:
- `python tools/studies/scan.py --base benchmarks/DEFAULT_BASE.json --var Bt_T --lo 4 --hi 6 --n 21`

## Constraint sweep
Same as scan, but focuses on dominant constraints and margins.

CLI:
- `python tools/studies/constraint_sweep.py --base benchmarks/DEFAULT_BASE.json --var R0_m --lo 5 --hi 8 --n 21`

## Scenario sweep
Replay the same point across scenarios (financing/availability/tech modes).

CLI:
- `python tools/studies/scenario_sweep.py --base benchmarks/DEFAULT_BASE.json --scenarios scenarios/example_scenarios.yaml`

Outputs are written under `artifacts/studies/` as JSON + CSV for easy plotting.
