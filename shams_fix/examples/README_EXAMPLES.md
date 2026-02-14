# v83 Examples (Additive Tools)

These examples demonstrate the **v83 PROCESS-compatibility tools**:
- Feasible Scan export
- Feasible Pareto filtering (feasible-only)
- SHAMS → PROCESS handoff envelope export

## 0) Environment
From the repository root (folder `SHAMS_FUSION_X_v83/`), ensure your normal SHAMS environment is active.

If you already have a working v79/v83 setup, nothing changes.

## 1) Feasible Scan (feasibility + margins)
Run a 1D scan over a single input variable (example: `R0`):

```bash
python -m tools.studies.feasible_scan   --base examples/base_point.json   --var R0   --lo 2.0   --hi 5.0   --n 31   --outdir out_feasible_scan_R0   --topk 5
```

Outputs:
- `out_feasible_scan_R0/feasible_scan.json` (full records including constraint margins)
- `out_feasible_scan_R0/feasible_scan_summary.csv` (lightweight summary)

## 2) Feasible Pareto (feasible-only)
Compute a Pareto subset using user-declared objectives **within the feasible points only**.

Example (adjust objective keys to match your outputs):
```bash
python -m tools.studies.feasible_pareto   --feasible-scan-json out_feasible_scan_R0/feasible_scan.json   --objectives R0:min
```

Output:
- `out_feasible_pareto/feasible_pareto.json`

Notes:
- Objective keys are looked up first on the point record and then in `outputs`.
- Common objective candidates (depending on your model outputs) might include: `R0`, `Q`, `Pfus`, `Pnet`, etc.

## 3) SHAMS → PROCESS Handoff Envelope
Export an empirical feasible envelope (from the scan results) that an optimizer can use as bounds.

```bash
python -m tools.studies.process_handoff   --feasible-scan-json out_feasible_scan_R0/feasible_scan.json   --out shams_process_handoff_R0.json
```

Output:
- `shams_process_handoff_R0.json`

## Troubleshooting
- If `PointInputs` rejects a field in `base_point.json`, remove or rename that field.
- Use your existing known-good SHAMS input JSON as `--base` if you have one.


## 4) Optimization Sandbox (SAFE)
Rank feasible points (no constraint relaxation) and re-audit top-10:

```bash
python -m tools.sandbox.sandbox_optimize \
  --feasible-scan-json out_feasible_scan_R0/feasible_scan.json \
  --objectives R0:min:1.0 \
  --topk 20 \
  --outdir out_sandbox
```


## 5) External Proposer Adapter (PROCESS downstream)
Prepare a JSON file `external_candidates.json` containing a list of candidate design dicts.

Then audit + rank (optionally merge with an existing feasible scan):

```bash
python -m tools.sandbox.external_proposer \
  --candidates-json external_candidates.json \
  --feasible-scan-json out_feasible_scan_R0/feasible_scan.json \
  --objectives R0:min:1.0 \
  --topk 20 \
  --outdir out_external_adapter
```
