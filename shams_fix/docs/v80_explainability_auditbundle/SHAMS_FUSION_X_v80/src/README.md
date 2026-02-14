# Phase-1 "Clean Point Design" Refactor (Drop-in compatible)

This folder extends the Phase-1 0‑D scan with **explicit screening models** to support a
cleaner HTS compact tokamak *0‑D point design* while keeping the original entrypoints
and Excel output conventions.

## What’s added (screening models)

These are **proxies** (not validated design tools), but they are explicit, parameterized,
and therefore easy to replace with Phase‑2 models.

1. **Radial build closure + TF peak field mapping + hoop-stress proxy**
2. **HTS (REBCO-like) critical margin proxy vs (B,T) + dump voltage proxy**
3. **Divertor heat flux constraint surrogate** using λq + wetted area + divertor radiation fraction
4. **Neutronics feasibility surrogates**: TBR proxy + HTS fluence lifetime proxy
5. **Recirculating power closure**: aux + current drive + cryo + pumps → net electric

Implementation is in `phase1_systems.py`, called from `phase1_core.hot_ion_point()`.

## Files

- `phase1_models.py` — reusable 0‑D physics models (IPB98, Martin‑08, Bosch–Hale, proxies)
- `phase1_systems.py` — systems/engineering proxy models (the “clean point design” additions)
- `phase1_core.py` — point calculation + nested solvers (now includes the new screening outputs)
- `phase1_hot_ion_ext.py` — wrapper preserving older function names
- `phase1_hf_compact_conf_improvement_scan_v2.py` — scan driver + Excel output

## Run

```bash
python phase1_hf_compact_conf_improvement_scan_v2.py --out_xlsx my_scan.xlsx
```

Optional failures sheet:

```bash
python phase1_hf_compact_conf_improvement_scan_v2.py --write_failures
```

## Notes / Limitations

- Still **0‑D**, volume‑averaged, steady-state.
- No equilibrium or transport solver.
- Divertor, neutronics, magnet protection are **screening proxies** only.
- Every assumption is exposed via CLI flags so you can tune or replace models cleanly.

## Continuing in a new chat
When moving to another conversation, upload the current project zip and mention:
- The version name (zip filename) you are using
- Any recent errors/tracebacks and where they occurred
- The intended next change (physics, solver, constraints, UI, docs)

This repo is designed so the assistant can work from the uploaded zip alone.
