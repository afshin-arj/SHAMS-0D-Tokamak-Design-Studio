# Point Designer publication benchmark pack

This folder contains a small, deterministic runner that produces **publication-ready tables** for
Point Designer, evaluated under **Research** and **Reactor** design intents.

Nothing here changes physics. It is a reproducible workflow wrapper around the frozen evaluator.

## Run
From repo root:

```bash
python benchmarks/publication/run_point_designer_benchmarks.py \
  --cases benchmarks/publication/cases_point_designer.json \
  --outdir benchmarks/publication/out
```

Or run the built-in reference presets (qualitative envelopes):

```bash
python benchmarks/publication/run_point_designer_benchmarks.py --use-reference-presets
```

## Output
`--outdir` will contain:
- `point_designer_benchmark_table.csv` — one row per case
- `artifacts/<case_id>.json` — per-case artifact with inputs, outputs, and intent-aware constraint classification

## Publication guidance
The shipped cases include:
  - Inspired envelopes (ITER/JET/DIII-D/SPARC/ARC...) for workflow validation
  - Literature-anchored starters:
    - STEP Prototype Plant baseline (UKAEA, 2023)
    - EU DEMO low-aspect-ratio size points (2024)

For a paper, you should:
  1) Replace/override any placeholder fields (e.g. Ti, fG, Paux, Ip if not supplied)
  2) Cite the exact table/figure source for every *input* row you publish
  3) Include the generated per-case artifacts in your supplementary material
