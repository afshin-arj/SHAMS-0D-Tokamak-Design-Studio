# PATCH NOTES — v407.0.0

## Upgrade: Nuclear Data Authority Deepening (multi-group + dataset provenance)

### What shipped

- **New authority (v407):** `Nuclear Data Authority Deepening`
  - Deterministic, algebraic **multi-group (default 6-group)** attenuation overlay.
  - **Explicit dataset registry** (`SCREENING_PROXY_V407`) with **SHA-256 provenance pinning**.
  - Outputs:
    - group edges, FW spectrum fractions (mapped from v403 3-group when available),
    - attenuation factors per group to TF-case,
    - TF-case fluence per group and total (`tf_case_fluence_n_m2_per_fpy_v407`),
    - bounded multi-group **TBR screening proxy** (`tbr_mg_proxy_v407`).

- **Integration:** v401 contract tiers now prefer `tf_case_fluence_n_m2_per_fpy_v407` (when v407 enabled) ahead of the v392 TF-case fluence proxy.

- **UI wiring:** new expander in the Physics panel to enable v407 and select dataset/group structure. Output view includes a v407 ledger expander.

### Model status / scope

- v407 is a **governance-only screening overlay**. It does **not** implement neutron transport, spectral iteration, depletion, or a nuclear data processing pipeline.
- The default dataset is explicitly labeled **not ENDF/TENDL-derived** and is intended for deterministic sensitivity ranking and auditability.

### Files added

- `src/nuclear_data/` (group structures + dataset registry)
- `src/analysis/nuclear_data_authority_v407.py` (+ shim `analysis/nuclear_data_authority_v407.py`)

