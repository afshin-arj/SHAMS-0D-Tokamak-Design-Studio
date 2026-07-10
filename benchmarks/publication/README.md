# Point Designer publication benchmark pack

This folder contains a small, deterministic runner that produces **publication-ready tables** for
Point Designer, evaluated under **Research** and **Reactor** design intents.

Nothing here changes physics. It is a reproducible workflow wrapper around the frozen evaluator
(`Evaluator.evaluate` → `hot_ion_point`).

## Case sets (split for paper claims)

| File | Use |
|------|-----|
| `cases_inspired.json` | Qualitative screening envelopes (ITER/JET/…-inspired). **Do not** claim paper reproduction. |
| `cases_literature.json` | Literature-oriented geometry (STEP, EU DEMO, SPARC/ARC-class). Cite sources; placeholders remain for Ti/fG/Paux. |
| `cases_for_paper.json` | Include-wrapper → literature only (preferred for paper tables). |
| `cases_point_designer.json` | Include-wrapper → inspired **+** literature (default NiceGUI pack). |

## Run
From repo root:

```bash
# Combined (default)
python benchmarks/publication/run_point_designer_benchmarks.py \
  --cases benchmarks/publication/cases_point_designer.json \
  --outdir benchmarks/publication/out

# Literature only (paper claims)
python benchmarks/publication/run_point_designer_benchmarks.py \
  --cases benchmarks/publication/cases_for_paper.json \
  --outdir benchmarks/publication/out_lit

# Inspired screening only
python benchmarks/publication/run_point_designer_benchmarks.py \
  --cases benchmarks/publication/cases_inspired.json \
  --outdir benchmarks/publication/out_inspired
```

Or run the built-in reference presets (qualitative envelopes):

```bash
python benchmarks/publication/run_point_designer_benchmarks.py --use-reference-presets
```

The NiceGUI **Publication Benchmarks → Tab 2** pack generator calls `run_publication_pack` **in-process**
(with per-case progress), not via subprocess.

## Output
`--outdir` will contain:
- `point_designer_benchmark_table.csv` — one row per case
- `artifacts/<case_id>.json` — per-case artifact with inputs, outputs, and intent-aware constraint classification
- `topology.json` / `summary.json` — pack-level fractions and SHAMS version stamp

## Publication guidance
For a paper, you should:
  1) Use `cases_for_paper.json` / `cases_literature.json` (not inspired alone)
  2) Replace/override any placeholder fields (e.g. Ti, fG, Paux, Ip if not supplied)
  3) Cite the exact table/figure source for every *input* row you publish
  4) Include the generated per-case artifacts in your supplementary material
