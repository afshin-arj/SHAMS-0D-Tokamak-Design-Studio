# SHAMS–FUSION-X: PROCESS-Inspired Systems Upgrade (Scientific Specification)

This document is a **scientific, implementable specification** for the PROCESS-inspired upgrades in SHAMS.
SHAMS is **Python-only**, Windows-native, and does **not** call PROCESS/Fortran, but follows the same *systems-code* mindset.

## 1. Canonical run artifact (SHAMS analogue of PROCESS MFILE)

PROCESS plotting tools consume a single canonical output file (`MFILE.DAT`) and can be auto-generated via `--full-output`. citeturn0view0

SHAMS now supports a **single canonical JSON artifact**:
- `shams_run_artifact.json`
- Contains `inputs`, `outputs`, and `constraints` with margins.
- All plot/report utilities consume this artifact (not the live solver).

## 2. Analytic 1/2-D profiles (core + pedestal)

SHAMS provides optional analytic profiles (normalized minor radius `ρ ∈ [0,1]`) with cylindrical proxy volume weighting:
- `dV ∝ 2ρ dρ`
- `⟨f⟩ = ∫ f(ρ) 2ρ dρ`

Profiles are used to compute *consistent averages* feeding 0-D models.

## 3. Constraint-driven closure

PROCESS is a systems code that computes plant parameters **self-consistently** under operating limits, optionally optimizing objectives. citeturn0view1

SHAMS uses the same philosophy:
- Targets (e.g. `Q`, `H98`) are solved by varying coupled variables (e.g. `I_p`, `f_G`).
- Hard constraints are reported as explicit objects with margins.

## 4. Plotting utilities (PROCESS-inspired)

PROCESS provides plotting tools that operate on the canonical output file:
- `plot_proc.py` summary PDF
- `plot_scans.py` scan visualization
- `plot_radial_build.py` radial build
- `plot_plotly_sankey.py` plant power Sankey citeturn0view0

SHAMS provides analogous tools that operate on the canonical JSON artifact:
- `tools/plot_shams_summary.py` → summary PDF
- `tools/plot_shams_radial_build.py` → radial build PNG
- `tools/plot_shams_sankey.py` → power-balance Sankey HTML (requires Plotly)

## 5. UI: explainability and exports

The Streamlit UI now exposes:
- downloadable JSON artifact
- radial build PNG export
- summary PDF export

This supports auditability and repeatability (key systems-code requirements).

