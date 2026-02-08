# Epoch Feasibility (v258.0)

Epoch Feasibility is a **constitutional** (semantic) overlay that evaluates a single frozen run artifact under a small set of lifecycle epochs:

- **Startup**
- **Nominal**
- **End-of-Life**

This feature is **not** time marching and does **not** introduce iteration. It reclassifies constraint enforcement
deterministically (hard / diagnostic / ignored) to reflect staged operational requirements.

## What it is

- A post-processing report attached to every `shams_run_artifact.json` as:

```json
"epoch_feasibility": {
  "schema_version": "epoch_feasibility.v1",
  "overall": "PASS|PASS+DIAG|FAIL",
  "epochs": [ ... ]
}
```

## What it is not

- Not an ODE/DAE time-domain simulation
- Not a controller synthesis tool
- Not an optimizer or feasibility recovery loop

## Rationale

Real plant reviews are epoch-dependent (commissioning vs nominal vs end-of-life). SHAMS supports this
without contaminating truth: the evaluator remains frozen; epochs are additional semantic lenses.
