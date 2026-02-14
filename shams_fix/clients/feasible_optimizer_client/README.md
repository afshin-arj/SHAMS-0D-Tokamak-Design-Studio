# Feasible-Only Optimizer Client (External to SHAMS)

This folder contains a **client-side** optimization driver that sits *on top* of SHAMS.

## Non-contamination contract

* The SHAMS evaluator (`src/evaluator/Evaluator`) remains the **single source of truth**.
* This client **never edits** SHAMS physics, constraints, or calibration.
* All optimization is **feasible-only**: infeasible points are recorded and discarded (they remain valid results).
* Deterministic: fixed RNG seed, fixed sampling schedule, reproducible artifacts.

## What it does

* Samples candidate inputs within user-provided bounds (uniform random).
* Evaluates SHAMS deterministically.
* Computes constraint pass/fail using the frozen constraint set.
* Keeps a feasible pool and (optionally) selects the best point under an explicit objective.

## What it does **not** do

* No hidden convergence, no mutation of the evaluator, no constraint relaxation.
* No “best machine” recommendations inside SHAMS.

## Quick start

```bash
cd clients/feasible_optimizer_client
python feasible_opt.py --bounds bounds_example.json --objective P_net_MW --n 200 --seed 0
```

Artifacts are emitted to `clients/feasible_optimizer_client/_out/`.


## v230.0 UI integration

This client is launched from the SHAMS UI in **Pareto Lab → Feasible Optimizer (External)**.
The UI writes a config JSON and starts this script with the same Python runtime as Streamlit.
Runs are recorded under `runs/optimizer/<run_id>/` as deterministic evidence packs.

CLI usage remains supported (legacy), but UI-driven `--config` is preferred.
