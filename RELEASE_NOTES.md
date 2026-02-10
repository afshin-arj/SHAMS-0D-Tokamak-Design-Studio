## v331.0 — External Optimization Interpretation Layer + Exit UI Wiring Audit

**Governance upgrade:** interpretation-only tooling to explain external optimizer outcomes (feasibility attrition, dominant-killer histograms, reviewer narratives), while preserving frozen truth.

- New contract (metadata only): `contracts/optimizer_capability_registry.json`
- New interpretation engine: `src/extopt/interpretation.py` (no optimization; consumes traces)
- New UI deck: **Pareto Lab → 🧪 External Optimization Interpretation**
  - Loads `optimizer_trace.json` (last run) or user-uploaded trace
  - Produces deterministic attrition tables, dominance breakdowns, and a reviewer-safe narrative
- Exit UI button visibility fix: **Exit SHAMS** is now rendered in the sidebar Activity Log section with a confirm latch (always visible; no phantom wiring)

Non-goals preserved: no solvers, no iteration, no internal optimization.

---

## v330.0 — Authority Dominance Engine

**Governance upgrade:** deterministic identification of the **dominant feasibility killer authority** (PLASMA / EXHAUST / MAGNET / CONTROL / NEUTRONICS / FUEL / PLANT), plus a top-k limiter table.

- New post-processing engine: `src/provenance/authority_dominance.py`
- Run artifacts now include: `authority_dominance` (schema `authority_dominance.v1`) and convenience fields: `dominant_authority`, `dominant_constraint`, `dominant_mechanism` (mapped to authority for legacy dashboards)
- UI: **Provenance → Authority Dominance** tab renders dominance verdict, ranked authorities, and top limiting hard constraints

Non-goals preserved: no solvers, no iteration, no optimization inside truth.

---

## v329.0 — Exhaust & Radiation Regime Authority

**Authority upgrade:** deterministic exhaust regime classifier (attached / marginal_detach / detached / radiation_dominated / overheat) with fragility margins and contract hash stamping.

- New immutable contract: `contracts/exhaust_radiation_regime_contract.json`
- New loader + classifier: `src/contracts/exhaust_radiation_regime_contract.py`
- Frozen evaluator now emits: `exhaust_regime`, `exhaust_fragility_class`, `exhaust_min_margin_frac`, `exhaust_detach_metric_MW_m`, `exhaust_q_margin_MW_m2`, `exhaust_radiation_dominated`, `exhaust_contract_sha256`
- UI: Point Designer → Physics Deepening → **Edge/Divertor & Exhaust Control** shows regime + fragility when available

No solvers, no iteration, no optimization inside truth.

---

## v328.0 — Magnet Technology Authority 4.1 (2026-02-10)

- Added explicit magnet technology regimes (**LTS / HTS / Cu**) governed by a deterministic contract: `contracts/magnet_tech_contract.json`.
- Truth outputs now include: `magnet_regime`, `magnet_contract_sha256`, `J_eng_A_mm2`, `quench_proxy_margin`, and `magnet_margin_min` with a fragility class (FEASIBLE/FRAGILE/INFEASIBLE).
- Constraint set expanded with regime consistency, TF engineering current density, coil thermal/nuclear budget checks, temperature window checks, and quench proxy check (all deterministic, no solvers).
- UI: Point Designer → Truth Console now renders a dedicated **Magnet Authority** panel (contract hash + key limits/margins).

## v327.9.2 — Exit UI Button Hotfix (2026-02-09)

- Added a professional **Exit SHAMS** button in the sidebar (confirm-to-exit) to cleanly terminate the Streamlit process without stack traces.
- Implemented as UI-only control in `ui/app.py` using `_os._exit(0)` (truth and artifacts unchanged).

## v327.5 — DSG subset linking from table selections
- Added Streamlit-only subset linker for tables carrying `dsg_node_id` (no truth re-runs).
- Integrated best-effort subset-link UI into Pareto, Trade Study, and ExtOpt tables.
- Added `ui/dsg_subset_linker.py` and a handoff wrapper in `ui/handoff.py`.

## v327.3 — DSG Pipeline Edge Automation (2026-02-09)

- Added DSG support for **edges between existing nodes** (`DesignStateGraph.add_edge/add_edges`) to attach lineage for batch pipelines without re-evaluating truth.
- Scan Lab now records **scan-feasible points into DSG** and exposes `scan_last_node_ids` + `scan_last_parent_node_id` for downstream linkage.
- Cross-panel candidate promotion (`stage_pd_candidate_apply`) now computes the deterministic **predicted node_id** and populates pipeline linkage slots for Scan/Pareto/Trade/ExtOpt.
- Rebuilt `ui/dsg_panel.py` (fixed indentation) and added **Pipeline edge capture** buttons to link last Scan/Pareto/Trade/ExtOpt sets.

Non-goals (preserved): frozen truth unchanged; no internal optimization; no solver creep.

## v327.2 — DSG Node Binding Contracts (2026-02-09)

- Added DSG→UI binding layer (`ui/dsg_bindings.py`) enabling **Adopt active DSG node into Point Designer** (UI-only).
- Added best-effort conversion helpers to DSG for PointInputs-like reconstruction.
- Added UI toggle to auto-set edge kind by active panel.

Non-goals (preserved): frozen truth unchanged; no internal optimization; no solver creep.

## v327.1 — DSG Active Node Selector & Lineage Breadcrumbs (2026-02-09)

- Added **DSG sidebar selector** (`ui/dsg_panel.py`) for choosing an active design node and declaring the **edge kind** context for downstream evaluations.
- Evaluator wrapper now records **lineage edges** from the selected node to new evaluations with explicit edge kind (derived/systems/scan/pareto/trade/extopt/repair).
- Reviewer Packet now includes `dsg/ACTIVE_NODE.md` when a DSG snapshot exists (best-effort).
- Added tests for lineage determinism and DSG panel summary generation.

Non-goals (preserved): frozen truth unchanged; no internal optimization; no solver creep.

## v327.0 — Design State Graph Inter-Panel Continuity (2026-02-09)

- Introduced a deterministic **Design State Graph (DSG)** (exploration layer) to persist evaluated design points and lineage across panels.
- Added Streamlit-side **DSG recorder** that wraps evaluator calls (no truth changes) and writes `artifacts/dsg/current_dsg.json` in canonical JSON form.
- Reviewer Packet now includes `dsg/CURRENT_DSG.json` by default (best-effort, never breaks packet build).

Non-goals (preserved): no solver/iteration added to truth; no internal optimization; frozen evaluator unchanged.

## v326.3 — UI Wiring Index Artifact + Reviewer Packet Integration (2026-02-08)

- Added static UI wiring index generator (`tools/ui_wiring_index.py`) that inspects `ui/app.py` without running Streamlit.
- Reviewer packet builder now includes `ui/UI_WIRING_INDEX.md` by default (reviewer-safe, deterministic).
- Added tests to guarantee presence of required wiring anchors and packet inclusion.

## v322.0 — One-Click Reviewer Pack Builder (Publication / Regulatory Artifact Export)

This upgrade hardens the **Reviewer Packet** into a complete, deterministic export bundle suitable for
review rooms and publication appendices.

### What changed
- Added a UI-agnostic builder: `tools/sandbox/reviewer_packet_builder.py`.
- Reviewer Packet now optionally includes:
  - Forge `report_pack/` (JSON + markdown + CSV)
  - Review Trinity `review_trinity/` (md + json)
  - Attack Simulation `attack_simulation/` (md + json)
  - Scan grounding `scan_grounding.json`
  - Replay capsule `run_capsule.json`
  - Do-not-build brief `do_not_build_brief.json`
  - Repo-level manifests and governance docs (`repo/`)
- Every packet includes an internal per-file SHA256 manifest: `MANIFEST_PACKET_SHA256.json`.

### UI
- 🎛️ Control Room → **Reviewer Packet** now provides a **Packet composition** expander and a
  manifest preview.

---

## v322.1 — Hotfix (Systems Solve UI precheck guard)

### Fixed
- Resolved a Streamlit rerun **NameError** where `do_precheck` could be referenced before
  definition in `ui/app.py` (dependent on conditional UI branches).
- Hardened related Systems controls (`do_continuation`, `cont_steps`) to persist via
  `st.session_state` and remain defined across reruns.

### Non-goals
- No changes to physics truth, constraints semantics, or solver behavior.

### Determinism / audit safety
- Stable JSON encoding (`sort_keys=True`) and deterministic ZIP ordering + timestamps.

Author: © 2026 Afshin Arjhangmehr

## v321.0 — Neutronics & Materials Authority 3.0 (Domain Tightening + Parity Dossier Expansion)

### Domain enforcement tightening
- Added explicit validity-domain checks for the TBR proxy (blanket thickness and coverage ranges) reported as `TBR_domain_ok`/`TBR_domain_margin`.
- New policy booleans: `neutronics_domain_enforce` and `materials_domain_enforce` (default False) to harden proxy-domain violations into hard constraints without modifying truth.
- Materials enforcement optional hardening: temperature-window and stress-proxy constraints become HARD when `materials_domain_enforce` is enabled.

### Parity dossier expansion
- PROCESS Parity Report Pack markdown now includes a Neutronics & Materials section (NWL, attenuation, nuclear heating, TBR, lifetimes, validity-domain status).

### UI
- ☢️ Neutronics panel adds domain enforcement toggles (off by default) and surfaces validity-domain status in verdict checks.

# v320.0 — Impurity Radiation & Detachment Authority 3.0

This upgrade implements the next locked roadmap step: **impurity radiation and detachment authority** in a deterministic, audit-safe way.

## What changed
- Extended the impurity contract species library to the required set: **C, N, Ne, Ar, W**.
- Upgraded radiation partitions to include **core / edge / SOL / divertor** (previously lacked explicit SOL).
- Added a deterministic **detachment inversion**: `q_div_target` → required SOL+divertor radiated fraction → implied impurity seeding fraction `f_z_required`.
  - No time-domain physics.
  - No iteration. Closed-form algebraic inversion using an Lz(T_SOL) envelope.
- Added an **optional soft feasibility cap**: `detachment_fz_max` enforces `f_z_required ≤ detachment_fz_max` (does not modify the operating point).

## UI wiring
- 🧭 Point Designer → Power & composition:
  - New expander: **Impurity radiation & detachment authority (v320)** with contract species, partitions, q_div target inversion, and transparency knobs.
- 🧰 System Suite → **Impurity & Radiation**: updated metrics for SOL partition and detachment inversion outputs.
- 🎛️ Control Room → Control contracts: SOL/detachment card now surfaces `f_SOL+div required`, `Prad_SOL+div required`, and `f_z required`.

## Law compliance
- Frozen evaluator remains algebraic and deterministic.
- Detachment authority is an explicit *budget* and inversion; it does not re-solve the plasma state.

Author: © 2026 Afshin Arjhangmehr

# v319.0 — Disruption & Stability Risk Tiering

This upgrade implements the next locked roadmap step: **deterministic disruption + stability risk tiering** as an advisory governance overlay.

## What changed
- Added **stability/control risk tiering** (`src/diagnostics/stability_risk.py`): LOW/MED/HIGH screening derived from existing truth outputs:
  - `mhd_risk_proxy` (monotonic proxy),
  - `vs_margin` (vertical stability margin proxy),
  - RWM screening (`rwm_control_ok`, `rwm_chi`),
  - control-contract minimum margin (`control_contract_margins`).
- Frozen evaluator now emits:
  - `stability_risk_tier`, `stability_risk_index`, `stability_dominant_driver`, `stability_risk_components`
  - `operational_risk_tier` and `operational_dominant_driver` as a unified screen (disruption + stability).
- Governance: **Decision Consequences** elevates operational risk drivers (MED/HIGH) when the design is otherwise hard-feasible.

## UI wiring
- Control Room → Chronicle now includes a new tab: **Stability Risk**.
- Displays stability tier + components, and unified operational tier/driver.

## Law compliance
- No solvers added; no iterations introduced.
- Tiering is strictly **diagnostic / advisory** and does not modify feasibility truth.

Author: © 2026 Afshin Arjhangmehr

# v318.0 — 1.5D Profile Proxy Bundle Hardening

This upgrade promotes the existing algebraic 1.5D profile bundle to a **first-class, UI-wired** capability while preserving SHAMS hard laws (no solvers, no iteration, frozen truth unchanged).

## What changed
- **PointInputs now includes profile authority knobs**: `profile_mode`, `profile_alpha_T`, `profile_alpha_n`, `profile_shear_shape`, `pedestal_enabled`, `pedestal_width_a` (defaults preserve legacy behavior).
- **Point Designer UI wiring** added under *Model options*:
  - enable/disable profile authority diagnostics
  - core profile exponents (α_T, α_n)
  - shear shape knob (0..1)
  - pedestal scaffold enable + width
- These knobs feed deterministic profile diagnostics in the frozen evaluator, including bounded bootstrap sensitivity when explicitly enabled.

## Law compliance
- No Newton / no hidden iteration.
- Profiles are diagnostic scaffolds; the operating point is not re-solved.

Author: © 2026 Afshin Arjhangmehr

## v316.0 — Feasible-First Surrogate Acceleration (Certified by Truth)

This upgrade improves SHAMS optimization throughput **without violating SHAMS law**: the surrogate is strictly non-authoritative and only proposes candidates. Every proposal is re-verified by the frozen evaluator.

### Feasible-First Surrogate Accelerator (Trade Study Studio)
- Added a deterministic surrogate module: `src/extopt/surrogate_accel.py`
  - ridge regression with a fixed quadratic feature map (no iterative training)
  - feasibility proxy learned from `min_margin_frac`
  - deterministic acquisition: predicted improvement + kappa · uncertainty
  - uncertainty proxy: residual σ × nearest-neighbor distance in normalized knob space
- Added a new Trade Study Studio deck: **⚡ Feasible-First Surrogate Accelerator**
  - proposes candidate batches from existing verified study rows
  - truth-verifies the batch and shows feasibility + margins
  - can append verified rows into the active Study Capsule
  - supports canonical promotion to 🧭 Point Designer

### Hygiene & discipline
- Truth remains unchanged; surrogate never writes to evaluator outputs.
- No new heavy dependencies (NumPy only).

Author: © 2026 Afshin Arjhangmehr

## v315.0 — Certified Optimization Orchestrator 2.0 (External, Governed)

This upgrade hardens SHAMS optimization ergonomics to feel turnkey like PROCESS **without violating SHAMS law** (no internal optimization, frozen truth, explicit constraints, auditable evidence).

### Certified Optimization Orchestrator 2.0
- Added a **hash-stable optimizer job object** (`OptimizerJob`, schema `optimizer_job.v1`) capturing kit, budget, bounds, objectives, and verification request.
- Added a **certified orchestrator runner** (`src/extopt/orchestrator.py`) that:
  - runs firewalled optimizer kits out-of-process,
  - ingests proposed best candidates from extopt evidence packs,
  - re-verifies each candidate against frozen truth via CCFS (`ccfs_verified.json`),
  - and writes a feasible-only certified set + Pareto subset (`certified_feasible.json`).
- Produces an auditable run directory under `runs/orchestrator/` with a sha256 manifest.

### UI wiring
- Added a new Pareto Lab deck: **🧾 Certified Optimization Orchestrator**.
- The deck provides "Run + Certify" and downloads for `ccfs_verified.json`, `certified_feasible.json`, and the manifest.

### Hygiene & discipline
- No changes to frozen evaluator physics.
- External optimization remains firewalled.

Author: © 2026 Afshin Arjhangmehr

## v309.0 — Neutronics & Materials Authority 2.0 (Proxy)

This single coherent upgrade implements the planned neutronics/materials authority deepening steps (v305–v309) while preserving SHAMS hard laws (frozen truth, feasibility-first, audit safety).

### Neutronics & nuclear loads
- **Fast vs gamma attenuation split** through the inboard radial stack: `neutron_attenuation_fast`, `neutron_attenuation_gamma`, with `neutron_attenuation_factor` mapped to the fast channel for backward compatibility.
- **Explicit nuclear-heating partitioning** across in-vessel regions + ex-vessel leakage allocations: `P_nuc_in_vessel_MW`, `P_nuc_leak_MW`, `P_nuc_TF_MW`, `P_nuc_PF_MW`, `P_nuc_cryo_kW`, plus a deterministic archetype selector `neutronics_archetype ∈ {standard, heavy_shield, compact}`.
- **Optional nuclear-load caps** (NaN disables): `P_nuc_total_max_MW`, `P_nuc_tf_max_MW`, `P_nuc_pf_max_MW`, `P_nuc_cryo_max_kW`.

### Materials authority (screening)
- **DPA + He production proxies** tied to neutron wall load and fast attenuation to region entrance:
  - `fw_dpa_per_year`, `fw_He_appm_per_year`, `fw_lifetime_yr`
  - `blanket_dpa_per_year`, `blanket_He_appm_per_year`, `blanket_lifetime_yr`
- **Temperature window checks** (no thermal solver): `fw_T_margin_C`, `blanket_T_margin_C` with optional enforcement flags `fw_T_enforce`, `blanket_T_enforce`.
- **Irradiation + temperature adjusted allowable stress proxy** (optional; NaN disables): `fw_sigma_allow_MPa`, `fw_sigma_margin_MPa`, `blanket_sigma_allow_MPa`, `blanket_sigma_margin_MPa`.
- **Expanded proxy materials library (v2)** with explicit units and conservative defaults.

### TBR proxy v2 (still proxy)
- Added explicit knobs: `port_fraction`, `li6_enrichment`, `blanket_type`, `multiplier_material`.
- Output fields: `TBR_margin` and `TBR_validity` flag (0 = nominal proxy range, 1 = out-of-range).

### UI wiring
- Point Designer exposes the new neutronics/materials knobs (fast optimistic) without creating scroll walls.
- Physics Deepening → **Neutronics & Nuclear Loads** panel shows the new attenuation split, DPA/He, temperature/stress margins, and TBR validity.

### Reviewer / evidence exports
- Dossier exporter now includes `materials_admissibility.json` when neutronics/materials keys are present.

### Hygiene
- No Qt remnants.
- Streamlit-only UI.
- No cache folders shipped (`__pycache__/`, `.pytest_cache/`).

Author: © 2026 Afshin Arjhangmehr

## v323.0 — Control Room Gatechecks Deck + Crashproofing Sweep

- Added **Control Room → Diagnostics → Gatechecks** panel: local commands + live hygiene scan.
- Rerun-safe Systems controls maintained (precheck/continuation guards).
- Hygiene sweep and manifest regeneration.

Author: © 2026 Afshin Arjhangmehr

## v323.1 — Systems Precheck/Solve Fix + Interoperability Audit

- Systems Mode precheck/solve path hardened:
  - deterministic safe defaults for first-run state
  - target/variable persistence across reruns
  - removed hidden-state disabled controls and silent no-ops
- Interoperability audit sweep across panels (canonical promotion paths): detects and reports cross-panel state mismatches.

Author: © 2026 Afshin Arjhangmehr

## v324.0 — Design Family Narratives & Regime Maps

### What changed
- Trade Study Studio adds **🗺️ Regime Maps & Narratives** deck:
  - deterministic clustering of *feasible* designs into families (quantized binning + deterministic merge; no solvers)
  - regime labels derived from **closest-to-violation** dominant constraints, enriched via `constraints.taxonomy`
  - per-cluster narrative synthesis: feature ranges + margin statistics + authority-tier metadata
  - reviewer-ready export: `regime_maps_report.json`

Author: © 2026 Afshin Arjhangmehr

## v325.0 — Certified Optimization Orchestrator 3.0 (Firewall + Objective Contracts)

### What changed
- Orchestrator upgraded with a **repo mutation guard** that detects any change to frozen areas (src/constraints/physics/models/profiles/schemas) during external kit execution.
- Introduced **objective_contract.v3** (explicit multi-objective contract with selection ordering) and persisted it per run.
- Added an **evidence-integrated optimizer dossier** (`optimizer_dossier.json`) linking:
  - kit run dirs under `runs/optimizer_kits/`
  - the specific evidence packs under `runs/optimizer/` used for candidate proposals
  - CCFS verification summary and certified feasible Pareto

### UI
- Pareto Lab → **🧾 Certified Optimization Orchestrator** deck updated to 3.0 and now emits objective contracts and dossier downloads.

Author: © 2026 Afshin Arjhangmehr

## v325.1 — Hygiene & UI Interop Audit Hardening

- Added `scripts/hygiene_clean.py` and made launchers run it automatically.
- Added bytecode suppression guards (`PYTHONDONTWRITEBYTECODE=1`) to reduce stray cache artifacts.
- Added a release hygiene gate (`tests/test_repo_hygiene.py`).

Author: © 2026 Afshin Arjhangmehr

## v326.0 — UI Interoperability Contract Validator

- Control Room adds **Interoperability contract validator (v326)**:
  - statically discovers subpanel functions in `ui/app.py` without importing Streamlit code
  - validates `ui.panel_contracts` coverage and contract sanity
  - optionally checks runtime presence of declared required session keys
  - emits a JSON report for reviewer-safe UI wiring audits

Author: © 2026 Afshin Arjhangmehr

## v326.1 — Public Repository Hardening

- Added `LICENSE` (Apache-2.0) and `NOTICE` with scientific/regulatory disclaimer.
- Added public-facing `README.md` and contributor docs (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`).
- Added `.gitignore` aligned with SHAMS hygiene rules (prevents caches and generated artifacts from being committed).
- Version bump only; **no changes to frozen truth**.

Author: © 2026 Afshin Arjhangmehr
## v327.2 — DSG Node Binding Contracts (UI Adoption + Auto Edge-Kind)
- Added deterministic DSG→UI bindings: adopt active DSG node inputs into Point Designer widget keys and Systems baseline (`ui/dsg_bindings.py`).
- Enhanced DSG sidebar with:
  - “Adopt active node into Point Designer” action (UI-only)
  - Auto edge-kind tagging by active panel (Systems/Scan/Pareto/Trade) with disable-able manual override.
- Extended DSG core with decoded inputs/outputs helpers and best-effort conversion to `PointInputs`.
- No physics truth changes; evaluator outputs unchanged.


## v327.4 — DSG Pipeline-native Node IDs

- Added pipeline-native `dsg_node_id` propagation into Scan/Pareto/Trade/ExtOpt tables when PointInputs columns are present.
- Added `ui/handoff.py` cross-panel staging helper to ensure promotions carry deterministic DSG node ids.
- Updated robust Pareto and Trade Study promotions to use the staging helper (no direct session_state mutation).
- Hygiene: removed cache directories from release.

Truth outputs unchanged.


## v327.6 — DSG Selection-native Subset Linking

- Removed dependence on multiselect UI widgets for DSG subset linking.
- Subset linker now supports deterministic **Top-N** selection with optional **stable sort** by a numeric column.
- Added power-user paste mode: link by pasting `dsg_node_id` list (comma- or newline-separated), filtered to ids present in the table.
- No truth re-runs; this upgrade only adds exploration-layer lineage edges.

Truth outputs unchanged.


## v327.7 — DSG table row-selection linking
- Added selection-native DSG subset linking using Streamlit dataframe row selection when available, with deterministic fallbacks.
- New UI helper: ui/table_select.py.
- Enhanced ui/dsg_subset_linker.py to offer row-selection capture inside the linker expander.


## v327.8 — Panel-native table selection capture
- Wrapped primary pipeline tables (Pareto, Trade Study) with Streamlit row-selection when supported.
- Selected `dsg_node_id` lists stored in session_state for DSG linking.
- No changes to frozen truth.

## v327.9 — Table-embedded DSG linking buttons
- Added one-click DSG lineage linking buttons embedded beside primary Pareto and Trade Study tables.
- New UI-only helper: `ui/dsg_actions.py` to attach DSG edges (exploration-layer only) and persist snapshot best-effort.
- No truth re-runs; no physics changes.

## v327.9.1 — Hotfix: optional matplotlib flag

- Fix `NameError: _HAVE_MPL is not defined` by defining `_HAVE_MPL` and `plt` as a safe, optional dependency in `ui/app.py`.
- UI plotting helpers now degrade gracefully when `matplotlib` is not installed (no crash; Streamlit fallbacks).

Truth outputs unchanged.
