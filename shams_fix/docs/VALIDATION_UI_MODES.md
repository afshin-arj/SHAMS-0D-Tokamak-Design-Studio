# UI Mode Physics & Logic Validation (Read-only)

This repository includes **read-only** scripts that exercise the four primary UI modes and
produce a machine-readable report.

Nothing in this workflow changes SHAMS behavior or alters any runtime models — it is *validation only*.

## Run

From the repo root:

```bash
python -m verification.run_ui_mode_benchmarks
```

This writes:

- `verification/ui_mode_benchmark_report.json`

## What it checks

1. **Point Designer**
   - Runs a single `hot_ion_point()` evaluation at the UI default point.
   - Confirms key outputs exist.
   - Summarizes constraint status.
   - Compares SHAMS `lambda_q_mm` to two literature references (Eich regression and Goldston heuristic drift model)
     using **wide tolerance bands** (magnitude / scaling sanity check only).

2. **Systems Mode**
   - Runs the coupled solve (targets: `Q_DT_eqv`, `H98`; variables: `Ip_MA`, `fG`) using the same solver used by the UI.
   - Records convergence flag, iteration count, message, and explicit residuals.
   - Summarizes constraint status at the solved point.

3. **Scan Lab**
   - Runs a small bounded sampling study and verifies the scan returns data structures expected by the UI.
   - Reports how many feasible points and pareto points are produced.

4. **Pareto Lab**
   - Verifies pareto extraction on a small point set works and returns a list.

## Interpretation

- A failure in this report usually indicates **wiring / logic / numerical robustness issues** (exceptions, missing keys,
  solver not converging), not that physics is "incorrect".
- Literature comparisons are **validation-only** and do **not** tune SHAMS.
