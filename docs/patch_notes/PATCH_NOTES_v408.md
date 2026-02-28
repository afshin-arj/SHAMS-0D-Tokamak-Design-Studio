# PATCH NOTES — v408.0.0

## v408.0.0 — Nuclear Dataset Intake & Provenance Builder (External, Firewalled)

Author: © 2026 Afshin Arjhangmehr

### Purpose

v407 introduced a deterministic multi-group nuclear data authority with an explicitly pinned dataset registry.
v408 extends this with a **firewalled intake pathway** for external datasets, enabling users to import
multi-group screening datasets with explicit provenance and SHA-256 pinning **without** introducing solvers
or Monte Carlo transport into SHAMS truth.

### What’s new

1. **Dynamic registry loader**
   - External datasets are stored under `data/nuclear_datasets/*.json`.
   - Registry enumerates built-in datasets + external datasets.
   - Shadowing built-in dataset IDs is forbidden.

2. **Strict intake validation (schema + vectors)**
   - New module: `src/nuclear_data/intake.py`
   - Supports:
     - Single dataset JSON (full schema)
     - Metadata JSON + sigma-removal CSV + user vectors
   - Enforces:
     - required keys
     - group-length consistency
     - spectrum fractions sum to 1.0
     - non-negative coefficients

3. **Provenance evidence card generation**
   - For each dataset, an optional deterministic evidence card can be written:
     - `data/nuclear_datasets/<dataset_id>.md`
   - Includes dataset SHA-256 of canonical payload.

4. **UI tooling (Streamlit)**
   - New deck expander:
     - `📥 Nuclear Dataset Intake & Provenance Builder — v408.0.0`
   - Upload + validate + save workflow.
   - The v407 selector now lists all datasets in the registry.

5. **CLI intake utility**
   - `python tools/nuclear_dataset_intake_cli.py --json <file.json>`
   - Also supports metadata+CSV intake.

### Hard-law compliance

- Frozen truth remains deterministic and algebraic.
- Intake is tooling-only and executed only on explicit user action.
- No Monte Carlo / transport solvers / spectral iteration added.
