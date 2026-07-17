# SHAMS Scoped PROCESS Retirement Evidence Report

**Schema:** `shams.process_retirement_report.v1`  
**SHAMS VERSION:** `v418.1.0`  
**Report SHA-256:** `e7f31d9121244996509947086162876ec51d4f025181c6848764556793e39a08`  
**Independence ticket:** 4.1 (Phase 4)

## Verdict (scoped — not a blanket claim)

- **Blanket PROCESS-retirement claim?** **NO**
- **Scientific release status:** **CONDITIONAL**
- **PROCESS parity corpus:** **METHOD-ONLY**
- **Summary:** SHAMS can serve the SCOPED_COVERED / PROXY_OVERLAY domains listed below as a feasibility authority with citeable VERSION + SHA-256 evidence. PROCESS is not retired. Domains under NOT_COVERED still need PROCESS, specialist codes, or are out of scope.

## Honesty constraints

- Do not claim PROCESS is retired.
- METHOD-ONLY parity does not authorize numeric PROCESS KPI claims.
- Scientific release status is CONDITIONAL — not APPROVED.
- Domains without evidence are listed as NOT_COVERED.
- Optimizers (including PROCESS) propose inputs only; SHAMS certifies.

- `process_retired_claimed`: `False`
- `numeric_parity_claimed`: `False`
- `invented_mfile`: `False`

## Domain coverage table

| Domain ID | Title | Coverage | PROCESS role |
|-----------|-------|----------|--------------|
| `ccfs_propose_only` | External optimization propose-only (CCFS) | **SCOPED_COVERED** | optional_proposer |
| `demo_match_overlays_proxy` | DEMO MATCH engineering overlays (proxy) | **PROXY_OVERLAY** | optional_proposer |
| `no_solution_attribution` | NO-SOLUTION mechanism attribution | **SCOPED_COVERED** | optional_proposer |
| `plant_kpi_honesty` | Plant KPI honesty watermark | **SCOPED_COVERED** | optional_proposer |
| `process_method_only_parity` | PROCESS parity honesty (METHOD-ONLY) | **SCOPED_COVERED** | legacy_reproduce_when_mfile_available |
| `process_migration_path` | PROCESS → SHAMS migration path | **SCOPED_COVERED** | handoff_documented |
| `scientific_release_conditional` | Scientific release readiness (CONDITIONAL) | **SCOPED_COVERED** | n_a |
| `tokamak_0d_feasibility` | Tokamak 0-D feasibility certification | **SCOPED_COVERED** | optional_proposer |
| `approved_zenodo_doi` | APPROVED scientific release + Zenodo DOI | **NOT_COVERED** | n_a |
| `bankable_cost_coe` | Bankable / institutional cost & COE authority | **NOT_COVERED** | still_needed_or_specialist_tools |
| `full_process_cli_breadth` | Full PROCESS-class coupled plant CLI breadth | **NOT_COVERED** | still_leads_for_breadth |
| `neutrals_edge_physics` | Neutrals / edge / scrape-off detailed physics | **NOT_COVERED** | specialist_codes |
| `process_numeric_parity` | PROCESS numeric KPI parity (MFILE-backed) | **NOT_COVERED** | still_needed_for_numeric_compare |
| `stellarator_ife` | Stellarator / IFE systems studies | **NOT_COVERED** | out_of_scope |

**Scoped covered / proxy count:** 8  
**Explicitly NOT covered count:** 6

## Covered / proxy domains (evidence-backed)

### `ccfs_propose_only` — External optimization propose-only (CCFS)

Optimizers (including PROCESS) may propose inputs only; SHAMS re-evaluates and refuses VERIFIED claims when hard constraints fail.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `optional_proposer`
- Evidence kinds: ccfs

### `demo_match_overlays_proxy` — DEMO MATCH engineering overlays (proxy)

Versioned MATCH overlays v410/v412/v419/v420/v421 provide magnet, build, Sankey, availability–OPEX–LCOE, and bottom-up costing narratives (OFF by default).

- Coverage: **PROXY_OVERLAY**
- PROCESS role: `optional_proposer`
- Limitation: Overlays are PROXY-labeled engineering coverage — not bankable cost models and not PROCESS MFILE clones.
- Evidence kinds: overlay

### `no_solution_attribution` — NO-SOLUTION mechanism attribution

Hard-infeasible runs stamp no_solution_atlas.v1 with dominant mechanism; infeasible champion cases exercise this path.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `optional_proposer`
- Evidence kinds: champion, atlas

### `plant_kpi_honesty` — Plant KPI honesty watermark

Healthy Pe_net / COE / LCOE are watermarked when hard-infeasible (plant_kpi_honesty.v1).

- Coverage: **SCOPED_COVERED**
- PROCESS role: `optional_proposer`
- Evidence kinds: plant_kpi

### `process_method_only_parity` — PROCESS parity honesty (METHOD-ONLY)

Hashed METHOD-ONLY delta dossiers record SHAMS side + mapping assumptions; PROCESS numeric KPIs remain null until a lab lands a licensed MFILE.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `legacy_reproduce_when_mfile_available`
- Limitation: METHOD-ONLY is not numeric parity. Do not claim PROCESS KPI agreement.
- Evidence kinds: parity

### `process_migration_path` — PROCESS → SHAMS migration path

Community migration guide maps IN.DAT→PointInputs, MFILE→artifacts, and CCFS propose-only citation practice.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `handoff_documented`
- Evidence kinds: migration

### `scientific_release_conditional` — Scientific release readiness (CONDITIONAL)

Phase 1.4 release gate verdict is CONDITIONAL with documented limitations; APPROVED / Zenodo DOI path is documented but not claimed.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `n_a`
- Limitation: Release status is CONDITIONAL — not APPROVED.
- Evidence kinds: release_gate, limitations

### `tokamak_0d_feasibility` — Tokamak 0-D feasibility certification

SHAMS frozen L0 evaluator + Design Intent hard set certify whether a tokamak point design is admissible; champion cases provide citeable packs.

- Coverage: **SCOPED_COVERED**
- PROCESS role: `optional_proposer`
- Evidence kinds: champion, version, ccfs

## NOT covered domains (explicit)

### `approved_zenodo_doi` — APPROVED scientific release + Zenodo DOI

Archival checklist and packaging exist; DOI is not minted and APPROVED verdict is not claimed while CONDITIONAL waivers remain.

- Why not covered: Release verdict remains CONDITIONAL; no DOI minted.
- PROCESS role: `n_a`

### `bankable_cost_coe` — Bankable / institutional cost & COE authority

v421 is a transparent modular CAPEX proxy, not a bankable cost model; do not treat it as Generomak/PROCESS cost truth.

- Why not covered: Economics overlays remain PROXY; no institutional cost validation pack.
- PROCESS role: `still_needed_or_specialist_tools`

### `full_process_cli_breadth` — Full PROCESS-class coupled plant CLI breadth

SHAMS serves feasibility authority + selective MATCH overlays; it does not clone PROCESS's full mutable megamodel / VaryRun operational lore.

- Why not covered: Independence ≠ feature-count clone; breadth remains selective MATCH.
- PROCESS role: `still_leads_for_breadth`

### `neutrals_edge_physics` — Neutrals / edge / scrape-off detailed physics

Not present as a SHAMS frozen-truth domain.

- Why not covered: Missing physics coverage in SHAMS L0 / authorities.
- PROCESS role: `specialist_codes`

### `process_numeric_parity` — PROCESS numeric KPI parity (MFILE-backed)

No licensed PROCESS MFILE / OUT.DAT extract is in-repo. Corpus stays METHOD-ONLY until a lab contributes provenance-tagged numerics.

- Why not covered: Missing licensed PROCESS reference KPIs.
- PROCESS role: `still_needed_for_numeric_compare`

### `stellarator_ife` — Stellarator / IFE systems studies

Outside SHAMS tokamak 0-D mission (IGNORE unless explicitly requested).

- Why not covered: Mission scope — not a tokamak 0-D feasibility domain.
- PROCESS role: `out_of_scope`

## Evidence index highlights

- VERSION file SHA-256: `44d7ed0923d8da81fac41b088363afca2ef724f3b8ef917fc3b69b4583378d2a`
- Champion pack SHA-256: `1af6a6d18c28dee4deb0c91d98fc768f653eb8f799b93d39e709ae00fa7a9a07` (4 cases; 2 feasible / 2 infeasible)
- Parity corpus status: **METHOD-ONLY** (corpus SHA-256: `eff27468bfb62bef260b503ef82a58f3809345f1e9a9ac4bb58b4c9414cd1e95`)

| Champion case | Hard feasible | Citation SHA-256 |
|---------------|---------------|------------------|
| `champion.reactor_conservative.iter_like` | True | `5235bb163ace13ce1764e4621890c00c5ba210a38b0b1925c8953e84b82dbcc8` |
| `champion.sparc_class.burning_plasma` | True | `b90d8912d54d33f50f0c8e15815009aee5566fcda7cb92745d903767675480ad` |
| `champion.sparc_class.overdriven_nosolution` | False | `ed40ba1ed234b2d57b77611af44b0c95a411865d654bbf0f869a7e8bfe70f0a5` |
| `champion.step_like.st_baseline` | False | `10f72a61268e8042a0efdf93d1102b42ed117c2e58ace19063913a321c750d3e` |

| Parity dossier | Status | File SHA-256 | Hash match |
|----------------|--------|--------------|------------|
| `method_only_hts_compact_001` | METHOD-ONLY | `7f6aff4fa98df6138a6cba6910c7b5193db8e7e95268ab866f46b07a5765fc54` | True |

| Overlay | Module | Exists | SHA-256 |
|---------|--------|--------|---------|
| v410 | `magnet_sc_system_authority_v410` | True | `5bc5e8f3e165da2cb8911270b3df5979a367ed254593e14ee46ec32a35be7e39` |
| v412 | `machine_build_authority_v412` | True | `43dd0ba994e829517da36b942ff7b5c533c98b31b48abb93dc27db7be056f8a1` |
| v419 | `plant_sankey_ledger_authority_v419` | True | `90b98a604920dfae3c8e110a667d143de292b7a13aeea13c88f34da7b9dd0abf` |
| v420 | `availability_opex_lcoe_authority_v420` | True | `a583754dd9f51395ddc2fe5a3ce8aac2734823aeefe5be301b48f928f3111706` |
| v421 | `bottom_up_costing_authority_v421` | True | `b90c49ae5cf2646ddac1de7160edea93160dd7f951d4b5fbd93b30d21455b906` |

## How to cite

1. Cite SHAMS `VERSION` exactly.
2. Attach this report's `report_sha256` plus relevant champion `citation_sha256` and/or parity dossier hashes.
3. State release status **CONDITIONAL** and parity status **METHOD-ONLY** unless newer evidence flips them.
4. **Do not claim PROCESS is retired.** Scope claims to the domain IDs above.

---

*Generated by `src/reports/process_retirement_report.py` (Independence Phase 4.1). L0 frozen truth untouched.*
