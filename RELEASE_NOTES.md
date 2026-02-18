# Release Notes

## v383.0.0 — Plant Economics & Cost Authority 2.0

- New: deterministic **Plant economics & cost authority (certified)** (governance-only; OFF by default).
  - Structured CAPEX proxy (prefers v356 component overlay when present).
  - Structured OPEX proxy: electricity (recirc + cryo + CD), tritium processing, maintenance, replacements, fixed OPEX.
  - Availability tiering (**A/B/C**) derived from disruption/control proxies → capacity factor used.
  - LCOE-lite proxy: `(FCR·CAPEX + OPEX)/E_net`.
  - New contract: `contracts/economics_v383_contract.json`.
- Systems Mode: adds a collapsed expander to render the cached v383 certification from the last Systems artifact.
- Feasibility-first: optional caps (NaN disables) added for structured CAPEX/OPEX and LCOE-lite.
- UI discipline preserved: compute → cache → render; no structural deck changes.

## v381.0.0 — Advanced Current Drive Library Authority (certified)

- New: **Current drive authority (certified)** in Systems Mode.
  - Deterministic certification computed from the last Systems artifact (**no solves, no iteration**).
  - Certifies **non-inductive fraction claims** (`f_NI`) using bootstrap + external CD currents when available.
  - Computes an effective CD efficiency proxy **η_cd = I_cd / P_CD** (MA/MW) and flags over-claimed efficiencies.
  - Adds **regime flags** (best-effort) using density thresholds: LH density limit, ECH high-density cutoff, NBI low-density shine-through risk.
  - JSON export: `systems_current_drive_certification_v381.json`.
- UI discipline preserved: button-driven compute → cache → render; no compute during render; no structural deck changes.

## v378.0.0 — Control & Actuation Authority (PF/RWM coupling deepening; certified)

## v380.0.0 — Impurity Radiation & Detachment Authority 3.0
- Added certified impurity radiation partition + detachment requirement inversion (no solvers, deterministic).
- Systems Mode: new collapsed expander under Key results (cache-only render).
- New contract: contracts/impurity_radiation_detachment_authority_v380.json


- New: **Control & actuation authority (PF/RWM, certified)** in Systems Mode.
  - Deterministic certification computed from the last Systems artifact (**no solves, no iteration**).
  - Adds explicit governance **actuator caps** (VS bandwidth/power, PF power, RWM power) and reports margin tiers.
  - Reuses the v374 stability/control mapping (vertical/RWM/volt-seconds) to avoid duplicating truth-output key semantics.
  - Adds a transparent **RWM power requirement proxy**: `P_rwm_req = P_ref * max(0, chi - 1)` (governance-only; tunable).
  - JSON export: `systems_control_actuation_certification_v378.json`.
- UI discipline preserved: button-driven compute → cache → render; no compute during render; no structural deck changes.

## v377.0.0 — Disruption Severity & Quench Proxy Authority (certified)

- New: **Disruption & quench authority (certified)** in Systems Mode.
  - Deterministic certification computed from the last Systems artifact (**no solves, no iteration**).
  - Adds a **disruption proximity index** (0..1) from βN proximity, q95 proximity, and Greenwald fraction (explicit weights).
  - Adds a **thermal quench severity proxy**: stored energy density **W/A** in **MJ/m²**.
  - Adds a **halo-current / force proxy**: I_halo range and force scaling **I_halo·B**.
  - JSON export: `systems_disruption_quench_certification_v377.json`.
- Fix (carry-in hardening): ships the missing module `src.certification.transport_confinement_certification_v376` referenced by the v376 UI.
- UI discipline preserved: button-driven compute → cache → render; no compute during render; no structural deck changes.

## v376.0.0 — Confinement & Transport Authority (H98 credibility certification)

- New: **Confinement & transport authority (certified)** in Systems Mode.
  - Deterministic certification computed from the last Systems artifact (**no solves, no iteration**).
  - Reports **H98 vs a conservative credibility envelope** (intent-aware: reactor tighter than research).
  - Exposes optional τE terms (`tauE_req_s`, `tauE_98_s`) if present in the artifact, and reconstructs H98 from them when needed.
  - Adds a single-step proportional probe (+1% by default) for local cliff awareness.
  - JSON export: `systems_transport_confinement_certification_v376.json`.
- UI discipline preserved: button-driven compute → cache → render; no cross-mode coupling; no UI restructuring.

## v375.0.0 — Exhaust & Divertor Authority v375 + Systems Mode Cached Post-Run Rendering

- New: **Exhaust & Divertor Authority v375** (deterministic) adds explicit bounds and transparency for SOL/divertor screening:
  - clamps *inputs* used by the divertor proxy (**λq**, **flux expansion**, **strike count**, **wetted fraction**) via an explicit JSON contract.
  - adds **unit/scale sanity flag** (`q_div_unit_suspect`) without modifying truth.
  - exports a certified bundle (raw vs used values + contract SHA) into outputs for governance/reviewer packs.
- UI: Systems Mode now **always renders** Key results + post-run expanders from the cached `systems_last_solution` artifact (no compute during render).
  - Fixes the symptom: “post-run results disappear after rerun / scroll.”
- UI: adds a collapsed expander **“🔥 Exhaust & Divertor Authority (certified)”** under **Key results**.
- No changes to: frozen evaluator discipline, cache keys, run IDs, or cross-mode coupling.

## v374.2.0 — Systems Mode Diagnostics Render Restore (Post-Key-Results)

- Fix: restored visibility of **Compact Cockpit** and **Systems Console** (verdict bar / why-chain / constraint cards) directly under the **Key results** section.
- Implementation: added a collapsed expander **“🔎 Detailed Systems Diagnostics (post-run)”** immediately after Key results outputs.
- Stability: removed the earlier duplicate diagnostics expander to avoid widget-key collisions and accidental gating.
- No changes to: frozen evaluator, Systems solve execution contract, cache keys, run IDs, or artifacts.

## v374.1.0 — Systems Mode Post-Key-Results Diagnostics Grouping (UI Non-Structural)

- UI-only refinement: moved **Compact Cockpit** and the **Systems Console** (verdict bar / why-chain / constraint cards) *below* “Latest Systems results (cached)”.
- Added a collapsed expander **“Detailed Systems Diagnostics (post-run)”** to reduce scroll fatigue and keep Key results as the primary anchor.
- No changes to: frozen evaluator, solver execution, cache keys, run IDs, artifacts, or cross-mode contracts.

## v374.0.0 — Stability & Control Margin Certification Authority (Systems Mode)

- New governance-grade certification: stability/control margins computed **from frozen truth outputs** (no solves, no iteration).
- Covers three reviewer-facing channels:
  - Vertical stability proxy margin (+ required bandwidth/power if control contracts enabled)
  - RWM proximity (chi) and regime classification
  - CS flux-swing (volt-seconds) headroom + optional loop-voltage cap margin
- Adds deterministic *fragility probes* (single-step 1% perturbations): κ (+1%), β_N (+1%), and I_p (+1%) to show local cliff-sensitivity.
- UI: new **Systems Mode** panel “Stability & control margin certification” with cache button and JSON export.
- Hygiene: manifests regenerated; no UI restructuring.

## v372.5 — UI Hotfix: Point Designer block scoping & tab variable safety (tab_tel)

- Fixed `NameError: tab_tel is not defined` by restoring correct scoping of the Point Designer block (indentation drift fix).
- Prevented lazy-tab variables from leaking outside the Point Designer deck.
- UI interop: ensured Point Designer always renders and navigation remains stable across reruns.
- Gatecheck/test hygiene preserved; manifests regenerated.


## v372.3 — UI Hotfix: Control Room tab scoping

- Fix: Control Room Diagnostics panel variable scoping: ensure `tab_pam` (and sibling tab handles) are only used inside the `🎛️ Control Room` deck.
- Fix: Remove stray top-level `with tab_pam:` block that caused `NameError: tab_pam is not defined` on app startup.
- Validation: `python -m py_compile ui/app.py` clean.

## v372.2 — UI Gatecheck + Deck Navigation Hotfix

- Fix: Gatecheck runner NameError by importing `subprocess` in UI.
- Fix: Replace Streamlit tab navigation with persisted sidebar deck selector (prevents rerun jump-back to Point Designer).
- Fix: Systems solve `max_iter` NameError caused by tab reset on rerun (resolved by persisted deck selector).
- Fix: Publication Benchmarks sub-tabs scope: ensure `_pb_tabs` is defined and used only inside the Publication Benchmarks deck (prevents `_pb_tabs` NameError).
- Fix: Transport Contracts v371: contract JSON loader + contract file; ensure import-safe and enabled when requested.
- Fix: Economics import hygiene: use relative imports in `src/economics/cost.py`.
- Validation: `pytest -q` passes.



## v372.0 — Neutronics–Materials Coupling Authority 2.0 (Governance)

- Adds governance-only neutronics–materials coupling diagnostics (material/spectrum-conditioned DPA-rate proxy).
- Provides component damage partitions (FW / blanket / structure) and lifetime proxy (FPY) under explicit allowable-DPA tables.
- Optional explicit constraints: effective DPA-rate cap and minimum damage margin (NaN disables).
- Fully wired into Point Designer UI (deck expander) and frozen truth post-processing; does not modify the operating point.

## v371.0 — Transport Contract Library Authority 2.0

- New governance authority: **Transport Contract Library (v371)**
  - Deterministic regime-conditioned (L/H) confinement envelope membership via existing Martin-2008 P_LH proxy
  - Frozen-truth post-processing only (does **not** modify operating point)
  - Explicit optimistic/robust caps on required confinement (*H_required*) as reviewer-visible, feasibility-first constraints
- Bugfix: removed duplicate `tauE_iter89p` definition in `src/phase1_models.py`
- UI (Point Designer)
  - New expander: “🚦 Transport contract library (v371)”
  - Telemetry deck now displays τE envelope min/max and pass flags for the optional caps
- New contract artifact: `contracts/transport_contracts_v371_contract.json`
- New test: `tests/test_transport_contracts_v371.py`

Truth outputs unchanged (unless the user explicitly enables the new caps as constraints).

---

## v368.0 — Maintenance Scheduling Authority 1.0

**New authority:** deterministic maintenance scheduling closure that converts replacement cadences + durations
into a schedule-dominated outage fraction and availability proxy.

Key additions:
- New module: `src/maintenance/scheduling_v368.py` (frozen-truth compliant; no solvers/iteration)
- New contract: `contracts/maintenance_scheduling_v368_contract.json` (hashed into artifacts)
- New outputs (when enabled): `availability_v368`, `outage_total_frac_v368`, and an explicit `maintenance_events_v368` table
- New constraints (optional):
  - `availability_v368 >= availability_v368_min`
  - `outage_total_frac_v368 <= outage_fraction_v368_max`
- Economics v360 now prefers maintenance-aware net generation and replacement annualization from v368 when present.
- Authority Dominance Engine now recognizes `MAINTENANCE` as a canonical authority label.

Truth outputs unchanged.

---

## v367.0 — Materials Lifetime Authority 1.0

**New authority:** deterministic materials lifetime closure that links neutronics/materials lifetime proxies to
plant design lifetime policy, replacement cadence, replacement counts, and annualized replacement cost rates.

Key additions:
- New module: `src/analysis/materials_lifetime_v367.py` (no solvers, no iteration)
- New contract: `contracts/materials_lifetime_v367_contract.json` (hashed into artifacts)
- Availability replacement ledger (v359) now includes FW/blanket annualized replacement cost rates if present
- New constraint group `materials_lifetime`:
  - optional minimum replacement cadence (FW/blanket)
  - optional hard policy enforcement: lifetime proxy must cover declared plant design lifetime
- Authority registry + dominance now recognize `MATERIALS` as a top-level driver.
- UI: Point Designer includes v367 policy knobs under Neutronics & Materials; Neutronics deep-view displays
  replacement counts/cadence and replacement cost rates.

---

## v366.0 — Multi‑Fidelity Authority Tiers (TRL Contracts)

- Adds **Multi‑Fidelity Authority Tiers** as a deterministic, reviewer-facing stamp (T0–T3) derived from the authority contract snapshot and (optionally) constraint-ledger involvement.
- New module: `src/provenance/fidelity_tiers.py` producing `artifact["fidelity_tiers"]` with:
  - `design_fidelity_label`, `design_fidelity_min_tier`, plus per-subsystem tiering and a SHA‑256 stamp.
- Artifact wiring: `src/shams_io/run_artifact.py` now attaches `fidelity_tiers` for every run (post‑processing only; frozen truth unchanged).
- UI: shows **Fidelity tier** badges in Verdict, Campaign Pack, Parity Harness, and Regime‑Conditioned Atlas panels.
- Tests: adds `tests/test_fidelity_tiers_v366_smoke.py`.

## v365.0 — Regime-Conditioned Pareto Atlas 2.0

- Adds **Regime-Conditioned Pareto Atlas 2.0**: partitions candidate sets by regime labels and governance class (dominance / robustness), and extracts per-bucket Pareto sets (no cross-regime mixing).
- New deterministic atlas core: `analysis/regime_conditioned_atlas_v365.py` (stable JSON fingerprinting; feasibility gating: optimistic/robust/robust-only).
- UI wiring: **📈 Pareto Lab** deck adds **🧭 Regime-Conditioned Pareto Atlas 2.0** with record uploader, bucket tables, per-bucket Pareto tables, and evidence-pack ZIP export.
- Evidence pack includes per-file SHA-256 manifest.

## v364.0 — PROCESS Benchmark & Parity Harness 3.0

- Added a deterministic benchmark case library (synthetic templates) for parity workflows.
- Implemented a parity runner that evaluates cases through the frozen evaluator and emits run artifacts.
- Added optional PROCESS intent-mapping + delta dossier generation (user-supplied PROCESS outputs).
- Added Streamlit System Suite tab: 🆚 Benchmark & Parity Harness 3.0 (fully wired, no phantom features).

## v363.0 — Optimizer-Ready Campaign Pack

- Adds **Campaign Pack (Optimizer-Ready)**: deterministic campaign specifications and bundle exports for external optimizers.
- New campaign modules:
  - `src/campaign/spec.py` (schema + validation)
  - `src/campaign/generate.py` (deterministic grid/LHS/low-discrepancy generation)
  - `src/campaign/export.py` (single ZIP export: candidates + assumptions + fingerprints + bundle manifest)
  - `src/campaign/eval.py` (deterministic batch evaluation producing evidence per candidate)
  - `src/campaign/cli.py` (minimal export/eval CLI)
- UI wiring: **🧰 System Suite** gains a new tab **🚀 Campaign Pack** (scope card; export + local eval; no auto-expansion).
- Governance: campaign exports include evaluator label, fixed-input assumptions, and Profile Contracts v362 fingerprint.

## v362.0 — Profile Contracts 2.0

- Adds **Profile Contracts 2.0**: a deterministic, finite-corner robustness screen over v358 profile-family knobs.
- New contract: `contracts/profile_contracts_v362_contract.json` (SHA-256 fingerprinted).
- New evaluator overlay: `src/analysis/profile_contracts_v362.py` producing:
  - optimistic_feasible vs robust_feasible,
  - MIRAGE flag (optimistic feasible but robust infeasible),
  - worst-corner min-margin summary,
  - per-corner constraint ledgers (hard/soft classification preserved).
- UI wiring: **🧰 System Suite** gains a new tab **📜 Profile Contracts 2.0** (scope card, no auto-expansion), plus deterministic ZIP export.
- Authority registry: adds `plasma.profile_contracts` (governance overlay; no truth modification).

## v361.0 — Engineering Actuator Limits Authority

- Adds explicit actuator-capacity constraints in the canonical constraints ledger (group: actuators) for:
  - Aux+CD wallplug electric draw cap (P_aux_total_el_MW ≤ P_aux_max_MW).
  - Current-drive installed capacity to meet NI target (P_cd_required_MW ≤ Pcd_max_MW).
  - PF envelope caps (I_peak, V_peak, P_peak, dI/dt, and pulse energy) when finite *_max caps are provided.
  - CS loop-voltage ramp cap (cs_V_loop_ramp_V ≤ cs_V_loop_max_V).
  - Optional peak power-supply cap: P_supply_peak_MW ≤ P_supply_peak_max_MW.
- Adds actuator authority contract: control.actuators (semi-authoritative) and dominance classification label ACTUATORS.
- Frozen evaluator remains algebraic: no solvers, no iteration; limits gate feasibility only when caps are finite.

## v360.0 — Plant Economics Authority 1.0

- Added deterministic plant economics authority (optional, OFF by default): CAPEX+Replacement+OPEX decomposition into availability-coupled LCOE proxy.
- New auditable OPEX breakdown outputs (recirc electricity, cryo wall-plug electricity, CD wall-plug electricity, tritium processing, maintenance, fixed OPEX).
- New optional feasibility caps (NaN disables): OPEX_max_MUSD_per_y and LCOE_max_USD_per_MWh applied to v360 outputs when enabled.
- Added contract fingerprinting: economics_v360_contract_sha256.

## v359.1 — Compare Session Slots Interop Hotfix

- Added session-based Compare Slot A/B interop: Point Designer can send the current run directly to Compare without file download/upload.
- Compare tab now supports session slots with metadata, download/clear controls, and optional upload-to-slot promotion.
- Added compare slot keys to UI cache invalidation to prevent stale cross-run confusion.

## v359.0 — Availability & Replacement Ledger Authority

- Added deterministic availability + replacement ledger overlay (planned/forced baselines + replacement downtime) (optional).
- Added v359 LCOE proxy output and optional caps (NaN disables) without modifying existing parity/economics outputs.
- Added contract fingerprinting for the v359 ledger authority.

## v358.0 — Profile Family Library Authority

- Added deterministic profile family library (transport proxy) with bounded confinement/bootstrap multipliers.
- Integrated profile family multipliers into confinement time (tauE) reporting and profile-bundle bootstrap proxy.
- UI: Point Designer includes a new "🧬 Profile family library (v358)" expander.
- Added contract fingerprint: profile_family_contract_sha256.

## v357.0 — Current Drive Library Expansion Authority (Channel Caps)

- Expanded **Current Drive / NI closure authority** with a deterministic channel-aware library: `cd_model=channel_library_v357`.
- New channel diagnostics (auditable outputs):
  - LHCD: declared n∥ and accessibility margins (contracted window + density ceiling proxy).
  - ECCD: launcher power density P_cd/A and declared launch factor.
  - NBI: shine-through fraction proxy and beam energy.
- New authority: `src/analysis/cd_library_v357_authority.py` + contract `contracts/cd_library_v357_contract.json` (SHA-256 fingerprinted).
- Optional hard feasibility caps (NaN disables) surfaced to the constraint ledger: LHCD n∥ bounds, ECCD launcher power density max, NBI shine-through max.
- UI wiring: **Engineering & plant feasibility** now exposes NI closure toggles and v357 channel knobs (deck-safe, no phantom features).
- Hygiene + manifests regenerated; version bumped.

## v356.0 — Cost Overlay Authority (CAPEX Cap)

- Added deterministic component CAPEX proxy and an optional hard cap (diagnostic feasibility screen).
- UI wiring: Engineering & plant feasibility adds CAPEX proxy controls.
- Manifests regenerated; hygiene enforced.

## v355.0 — Licensing Evidence Tier 2

- Added **Licensing Evidence Tier 2 (v355)** deterministic pack builder (schema v3): `tools/licensing_pack_v355.py`.
- Tier 2 pack adds: full contract fingerprint registry, authority audit snapshot, replay payload, optional regime transitions and v352 certification (when present).
- UI wiring: Publication Benchmarks now includes **Evidence exports** with both reviewer/regulator packs (v334) and Licensing Tier 2 (v355).
- Manifests regenerated; hygiene enforced.

## v354.0 — Scenario Templates (Industrial Use)

- Added industrial intent scenario templates (Pilot plant / Grid baseload / Compact HTS / Neutron source) as deterministic Point Designer presets.
- Added scenario JSON library under `scenarios/industrial_v354/` and a loader at `tools/industrial_scenario_templates_v354.py`.
- UI: new Point Designer control expander to preview and load templates (no solvers, no optimization).
- Hygiene: manifests regenerated.

# v353.0 — Regime Transition Detector

- Added **Regime Transition Detector (v353)** as a deterministic post-processing layer over the last Point Designer artifact.
- New module: `src/analysis/regime_transition_detector_v353.py` producing regime labels + near-boundary flags (no solvers, no iteration).
- Artifact integration: `regime_transitions` report + compact `tables.regimes` payload.
- UI: **🧰 System Suite** adds a new tab **🧭 Regime Transitions** (read-only, deck-safe).
- Manifests regenerated; version bumped.

# v352.0 — Robust Design Envelope Certification

- Added **Robust Design Envelope Certification (v352)** as a deterministic, budgeted governance layer over explicit candidate sets.
- New module: `src/certification/robust_envelope_v352.py` with tiering (A/B/C) based on worst hard margin under robust UQ corners.
- New contract: `contracts/robust_envelope_certification_contract.json` (fingerprintable, reviewer-safe).
- UI: new deck in **🧪 Trade Study Studio** with evidence ZIP download (report + optional corners).
- Hygiene and manifests regenerated.

## v351.0 — Multi-Objective Feasible Frontier Atlas

**Authority objective**: provide a descriptive, deterministic atlas over evaluated point sets: feasible envelope, robust envelope, mirage set, and empty-region maps.

What’s new:
- Trade Study Studio adds a new deck: **🗺️ Multi-Objective Feasible Frontier Atlas (v351)**.
- Feasible-only Pareto extraction for up to 4 objectives (no optimization; nondominated filtering only).
- Optional two-lane classification on the Pareto subset (budgeted): optimistic vs robust uncertainty contracts.
- Empty-region detection via deterministic 2D binning with downloadable atlas JSON.
- New module: `src/atlas/frontier_atlas_v351.py` (deterministic atlas utilities).

## v350.0 — Tritium & Fuel Cycle Tight Closure

**Authority objective**: provide a deterministic, algebraic fuel-cycle ledger that tightens tritium closure without any time-domain simulation or iteration.

What’s new:
- New contract: `contracts/tritium_fuelcycle_tight_closure_contract.json` (SHA-256 stamped).
- New inputs (optional; off by default): `include_tritium_tight_closure`, processing delay, inventory caps, loss fraction, and self-sufficiency margin.
- New outputs: burn throughput, reserve/in-vessel/total inventory proxies, effective TBR after losses, and self-sufficiency margins.
- New constraints (optional): in-vessel and total inventory caps; effective-TBR self-sufficiency requirement.
- UI: Point Designer → Engineering & plant feasibility adds a Fuel-cycle section (deck-compliant, no auto-expansion).

## v349.0 — Bootstrap & Pressure Self-Consistency Authority

**Authority objective**: enforce optional algebraic consistency between bootstrap fraction and pressure/beta regime proxies (no iteration).

(Release notes were missing in this file in prior baselines; added for continuity.)

## v346.0 — Current Drive Technology Regimes (CD-Tech Authority)

## v348.0 — Edge–Core Coupled Exhaust Authority

**Authority objective**: provide a deterministic, one-pass coupling between detachment-required SOL+divertor radiation and an inferred increment in core/edge radiation that reduces effective SOL power, then re-evaluates exhaust proxies **without any iteration**.

What’s new:
- **New authority switch**: `include_edge_core_coupled_exhaust` (default: off; no behavior change unless enabled).
- **Coupling knob**: `edge_core_coupling_chi_core` ∈ [0,1] maps required SOL+div radiation to additional core radiation: ΔP_rad,core = χ_core · P_rad,sol+div,req.
- **Optional cap**: `f_rad_core_edge_core_max` limits the coupled radiative fraction (screening constraint + contract cap).
- **New outputs** (when enabled): `P_SOL_edge_core_MW`, `edge_core_coupling_delta_Prad_core_MW`, `f_rad_core_edge_core`, plus `*_base` backups for divertor proxies.
- **UI wiring**: controls added under Impurity radiation & detachment authority panel (Streamlit deck, no auto-expansion).
- **Hygiene**: removed stray launcher under `examples/`, removed macOS `._*` artifact; added ignore rule.
## v347.0 — Non-Inductive Closure Authority (NI-Closure)

- Added deterministic NI closure authority (current balance + auxiliary electric power cap), contract-governed with SHA-256 fingerprint.
- New contract: `contracts/ni_closure_authority_contract.json`
- New analysis: `src/analysis/ni_closure_authority.py` (+ `analysis/` mirror)
- Evaluator stamps NI closure regime, fragility, min margin, and top limiter (failure-safe).
- UI: Physics Deepening adds “Non-Inductive Closure Authority” panel with expandable margins table.



- Added deterministic Current Drive Technology Authority with explicit CD actuator regimes (ECCD/LHCD/NBI/ICRF) and conservative envelopes on CD efficiency (A/W), wall-plug proxy, CD plant power fraction, and LHCD density accessibility proxy where available.
- Added governance contract `cd_tech_authority_contract.json` with SHA-256 fingerprint stamping into artifacts (`cd_contract_sha256`).
- UI: added Physics Deepening deck "Current Drive Tech Authority" (verdict-first, expandable margins table).

## v344.0 — Authority Contract Studio & Governance Validator 2.0

## v345.0 — Current Profile Proxy Authority (Bootstrap / CD / q-profile plausibility)

- Added deterministic Current Profile Proxy Authority (contract-governed): bootstrap fraction proxy bounds, q-profile proxy caps, CD feasibility proxies, NI consistency margin.
- Added `current_profile_proxy_authority_contract.json` with SHA-256 stamping in outputs.
- UI: Point Designer → Physics Deepening adds “Current Profile & Current Drive” diagnostics with expandable margin table.
- Hygiene + manifests regenerated.


- Added Contract Studio UI (Publication Benchmarks) to browse, validate, diff, and export governance contracts.
- Added deterministic contract validator with canonical JSON SHA-256 hashing and combined contracts fingerprint.
- Artifacts now include `contracts_used` and `contracts_fingerprint_sha256` derived from emitted `*_contract_sha256` keys.

## v343.0 — Interval Narrowing & Repair Contracts

- Added deterministic interval narrowing analysis (explanatory-only): flags dead regions (bins with zero PASS) and proposes advisory narrowed intervals from evaluated candidate sets.
- New module: `src/solvers/interval_narrowing.py` with evidence schema `interval_narrowing_evidence.v1` and governance artifact `repair_contract.v1`.
- UI: added Chronicle tab **Interval Narrowing** (read-only) with one-click evidence-pack export and repair_contract.json download: `ui/interval_narrowing.py`.
- Governance: added `contracts/repair_contract.json` (default contract template).
- Version bump to 343.0; manifests regenerated; hygiene enforced.

## v342.0 — External Optimizer Co-Pilot

- Added External Optimizer Co-Pilot (firewalled, interpretation-only orchestration): evaluate external candidate sets, write deterministic run folders, and export candidate dossiers.
- New module: `src/extopt/copilot.py` writes `optimizer_trace.json`, `interpretation_report.json`, `RUN_MANIFEST_SHA256.json`, and optional per-candidate evidence packs.
- UI: new Pareto Lab deck **🧭 External Optimizer Co-Pilot** (`ui/extopt_copilot.py`) for upload → batch evaluation → attrition narrative review → deterministic downloads.
- Version bump to 342.0; manifests regenerated; hygiene enforced.

## v341.0 — Feasible-first Surrogate Acceleration (Certified Search)

- Added a non-authoritative feasible-first surrogate stage to Certified Search Orchestrator (still external to frozen truth).
- UI: Certified Search now supports inserting a surrogate stage with explicit controls (budget fraction, pool multiplier, kappa, ridge alpha).
- Evidence: verifier now stamps `min_margin_frac` + `worst_hard` to support deterministic feasibility proxy training.
- Governance: added `contracts/feasible_first_surrogate_contract.json`; version bump to 341.0; manifests regenerated; hygiene enforced.

## v340.0 — Certified Search Orchestrator 2.0

- Upgraded Certified Search into a deterministic multi-stage orchestrator (external to frozen truth): `solvers/certified_search_orchestrator.py`.
- Added deterministic Halton sampler option (no external dependencies) and surfaced in UI (`lhs | grid | halton`).
- UI: Certified Search now supports optional two-stage local refinement; results are shown in an expandable table.
- Governance: added `contracts/certified_search_orchestrator_contract.json`; version bump to 340.0; manifests regenerated; hygiene enforced.

## v339.0 — Plasma–Engineering Coupling Narratives (Deterministic)

- Added deterministic coupling narrative engine (post-processing only): flags + reviewer-safe narratives derived from authority dominance, regime labels, and margins.
- UI: added *Coupling Narratives* sub-deck under 🧬 Physics Deepening (Point Designer) with expandable narratives.
- Governance: version bump to 339.0; manifests regenerated; hygiene enforced.

## v338.0 — Neutronics & Materials Authority Tightening

- Added deterministic neutronics/materials authority contract: `contracts/neutronics_materials_authority_contract.json`
- Added classifier with signed margins and regime labels (no solvers): `src/analysis/neutronics_materials.py`
- Evaluator now stamps neutronics/materials regime outputs + contract hash.
- UI: Neutronics deck now shows regime + fragility + min margin.
- README enforced to canonical text.

## v337.0 — Impurity Species & Radiation Partition Authority

- Added `contracts/impurity_radiation_authority_contract.json` (deterministic thresholds, hash-stamped).
- Added truth-safe contract loader and classifier (`src/contracts/impurity_radiation_authority_contract.py`, `src/analysis/impurity_radiation.py`).
- Evaluator stamps impurity regime, species, fragility, and signed fractional margins (no solvers, no iteration).
- UI: Physics Deepening now shows Impurity/Radiation regime block adjacent to Plasma regime.

# v336.0 — Plasma Regime Authority (Deterministic Regimes & Margins)

- Added plasma regime authority contract: `contracts/plasma_regime_authority_contract.json` (versioned, hashable).
- Added deterministic regime classifier: `src/analysis/plasma_regime.py` producing:
  - confinement + burn regime labels,
  - signed fractional margins for H-mode access, Greenwald fraction, q95, betaN, and burn (M_ign_total),
  - min margin + fragility class.
- hot_ion evaluator now stamps: `plasma_regime`, `burn_regime`, `plasma_*_margin_frac`, and `plasma_contract_sha256`.
- UI: Point Designer → ⚡ Mission Snapshot → 🧬 Physics Deepening → "Regime & Confinement" now shows Plasma Regime Authority summary.

No solvers, no iteration, no hidden relaxation; classification is read-only and truth-safe.

---

# v335.0 — Control & Stability Authority Hardening (Contracted Caps)

- Added deterministic control stability contract: contracts/control_stability_authority_contract.json
- Control contracts now accept contract-provided defaults for optional caps (no input mutation; truth-safe).
- hot_ion evaluator stamps control_contract_sha256 for reviewer packs.
- README.md synchronized to canonical project doctrine text.

---

# v334.0 — Licensing-Grade Regulatory & Reviewer Evidence Packs

- Upgrades evidence packs to schema v2 with strict required sections and pack-level `PACK_MANIFEST.json` (SHA-256 + metadata + contract fingerprints).
- Adds deterministic pack validator (UI + CLI): detects missing sections, hash mismatches, and schema violations (fails fast; no silent omissions).
- Adds publication-ready exports inside the pack: canonical CSV tables + a deterministic PDF summary report (static; no interactive dependencies).
- Adds batch pack builder support (multi-artifact packs) without modifying truth.

README remains pinned to canonical SHAMS doctrine text.

---

# v333.0 — Regulatory & Reviewer Evidence Packs

- Adds one-click deterministic Regulatory/Reviewer Evidence Pack ZIP export (CSV+JSON+contracts+SHA-256 manifest).
- New UI panel: 📚 Publication Benchmarks → 🧾 Regulatory Evidence Packs.
- README pinned to canonical SHAMS doctrine text.

---

## v332.1 — UI Determinism & Systems Solve Robustness Hotfix

- Fixed Streamlit widget ID collisions in **Phase Envelopes** and **Uncertainty Contracts** by adding deterministic `ui_key_prefix` keys (prevents "multiple ... elements with the same auto-generated ID" errors when panels are rendered in multiple UI contexts).
- Hardened **Systems Mode** solver knob persistence:
  - `systems_max_iter` is now seeded in session state on first entry and the Max Iterations control is keyed, preventing `NameError: max_iter is not defined` on first-run/rerun edge cases.
- Performance: cached Evaluator construction via `st.cache_resource` inside `_dsg_evaluator`, reducing UI latency on reruns/tab switches.

No changes to frozen truth physics semantics.

---

## v332.0 — Design Family Narratives

**Governance upgrade:** deterministic, interpretable **design-family clustering** over evaluated designs, replacing “best point” thinking with regime- and mechanism-based families.

- New deterministic family engine: `src/narratives/design_families.py`
  - Rule-based (no ML), stable across runs
  - Family keys built from labels already produced by SHAMS authorities:
    - intent, magnet regime, exhaust regime, dominant authority/constraint
    - coarse geometry buckets (R0/B0/A) for interpretability
  - Deterministic archetype selection (max margin; hash tie-break)
- New UI deck: **Pareto Lab → 🧬 Design Family Narratives**
  - Builds families from **Pareto** points or **all feasible** points (session-local)
  - Expandable family table + family narrative + archetype drill-down

Non-goals preserved: no optimization, no solvers in truth, no stochastic clustering.

---

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


## v372.4 — UI Hotfix: Point Designer Telemetry lazy-tab safety (run_btn)

- Fix NameError `run_btn` in Point Designer Telemetry caused by Streamlit lazy tab execution.
- Telemetry tab is now strictly cached/read-only: guides user to run Evaluate Point in Configure when no cached results exist.
- Replace Configure-tab-only log formatting with artifact-derived logging to prevent cross-tab NameErrors.
- Gatechecks: `py_compile ui/app.py`, full pytest suite.


## v374.1.1 — Systems Mode base-object access hardening hotfix

- Fixed Systems Mode crash when `base0` is a JSON-loaded dict by introducing a dict/dataclass-safe getter (`_safe_get`) and removing direct `base0.<field>` attribute access in fallback paths.
- No changes to solver execution, cache keys, run IDs, or UI deck structure.


## v381.0.1 — UI Hotfix (Streamlit widget key hardening)
- Fix StreamlitDuplicateElementId by adding explicit unique keys to duplicate `number_input` widgets labeled 'Probe fraction' (transport vs stability panels).

## v382.0.0 — Transport Profile Authority (1.5D-lite proxies)

- New governance-only certification: `src/certification/transport_profile_certification_v382.py`.
- New contract: `contracts/transport_profile_authority_v382.json`.
- Systems Mode: added collapsed panel **“🧩 Transport profile authority (certified) — 1.5D-lite proxies”** with cache-only compute and JSON export.
- Version bump + regenerated repo manifests.
