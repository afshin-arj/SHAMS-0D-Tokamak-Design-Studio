# 0‑D Physical Models in SHAMS (Phase‑1)

This document explains the **transparent, decision-grade proxy models** used by SHAMS–FUSION‑X in Phase‑1.
It is intentionally *not* a high‑fidelity plasma simulator: the purpose is **fast feasibility scanning**, **constraint tracing**, and **auditable trade studies**.

> Where to look in the code  
> Most calculations originate in `src/physics/hot_ion.py` (the “single point” evaluator), with supporting helpers in:
> `src/physics/` (plasma + engineering proxies), `src/engineering/` (radial stack), `src/economics/` (cost proxies).

---

## Geometry and core definitions

**Inputs (typical):** major radius `R0_m`, minor radius `a_m`, elongation `kappa`, toroidal field `Bt_T`, plasma current `Ip_MA`.

**Derived:** aspect ratio `A = R0/a`, plasma volume and surface area proxies, and simple shaping factors used by confinement / stability proxies.

---

## 0‑D plasma core (hot‑ion point model)

**Where:** `src/physics/hot_ion.py`

The core model computes a steady-state point with:
- temperatures (ion and electron) from inputs / ratios,
- density from a Greenwald fraction proxy,
- fusion power using a simplified reactivity proxy and volume-averaged assumptions,
- radiation and SOL power as transparent scalings with `Zeff` and input power.

Key outputs typically include `Pfus_DT_MW`, `P_rad_MW`, `P_SOL_MW`, and `Q_DT_eqv`.

---

## Confinement (IPB98‑like proxy)

**Where:** `src/physics/hot_ion.py` (confinement helper section)

SHAMS uses an **IPB98(y,2)-like structure** with an explicit confinement multiplier:
- base confinement time `tau_E98` from a power-law proxy,
- applied multiplier `H98` (input or derived),
- net confinement `tau_E = H98 * tau_E98`.

This is used consistently in:
- temperature / power balance proxies,
- robustness scans (uncertainty on `H98` is treated as epistemic if you choose).

---

## H‑mode access (L‑H threshold proxy)

**Where:** `src/physics/hot_ion.py` (H‑mode access)

SHAMS uses a **Martin‑08‑like** threshold proxy:
- threshold power `P_LH` depends on size, field, and density proxies
- access margin `LH_margin = P_SOL / P_LH`

The boolean feasibility key:
- `LH_ok = 1.0` if `LH_margin >= LH_margin_min` else `0.0`

(Constraints treat these booleans as “must be 1.0”.)

---

## Stability and operational limits (proxies)

**Where:** `src/physics/hot_ion.py`

- **q95 proxy**: a shaped proxy based on `Ip`, `Bt`, and geometry. Output: `q95_proxy`.
- **Normalized beta proxy**: volume-averaged proxy. Output: `betaN_proxy`.

These are used for feasibility screens, not detailed MHD.

---

## Magnets and engineering (TF peak field, stress, margins)

**Where:** `src/physics/hot_ion.py`, `src/physics/magnets.py` (if present)

Key engineering proxies:
- peak field mapping: `B_peak_T` as a transparent mapping from `Bt_T` and coil build geometry,
- hoop stress proxy: `sigma_hoop_MPa`,
- HTS margin proxy: `hts_margin` (if HTS assumptions are enabled).

---

## Radial build closure (explicit stack)

**Where:** `src/engineering/radial_stack_solver.py`

SHAMS treats inboard radial build as an explicit **stack of named layers**, each with:
- thickness `t_m`
- optional minimum thickness `min_thickness_m`

The solver reports:
- `inboard_space_m = R0 - a`
- `inboard_build_total_m` (sum of stack)
- `inboard_margin_m = inboard_space_m - inboard_build_total_m`
- `stack_ok = 1.0` if margin >= 0 and all mins satisfied else 0.0
- `radial_stack` list with per-layer thickness and min thickness

This is the primary “geometry closure” gate for feasibility-first workflows.

---

## Economics (lifecycle cost proxy)

**Where:** `src/economics/lifecycle.py`

SHAMS includes a **transparent lifecycle costing proxy**:
- parametric CAPEX and OPEX breakdown
- availability and replacement schedule hooks
- derived `LCOE_proxy_USD_per_MWh` and `NPV_cost_proxy_MUSD`

This is meant for scenario comparison and robust design ranking, not bankable cost estimation.

---

## Calibration and provenance (auditability)

**Where:** `src/calibration/registry.py`, `src/provenance/model_cards.py`

- Calibration factors are stored with **source**, **created time**, **validity ranges**, and **uncertainty notes**.
- Model cards record **what equations/assumptions are in use** and provide hashes so artifacts can be audited.

Every evaluated output includes `model_cards` (id → {version, sha256, module, entrypoint}).

---

## How to extend safely

1. Add/modify a model proxy.
2. Update (or add) a model card in `src/model_cards/`.
3. Add a requirement in `requirements/SHAMS_REQS.yaml`.
4. Add or update a verification case in `benchmarks/`.
5. Run: `python verification/run_verification.py` and ensure it passes.



## Phase‑2 engineering closures (PROCESS‑inspired)

### Magnet pack proxy (TF)
- Outputs: `tf_Jop_MA_per_mm2`, `tf_stress_MPa`, `cryo_power_MW`
- Purpose: connect field/size to current density limits, stress margin, and cryo power.
- Location: `src/engineering/magnets/pack.py`

### Tritium breeding ratio proxy (TBR)
- Outputs: `TBR`, `TBR_margin`, `TBR_validity`
- Purpose: monotonic proxy linking blanket thickness/coverage/enrichment to a breeding threshold.
- Location: `src/engineering/neutronics_proxy/tbr.py`

### Divertor/heat exhaust proxy (tech modes)
- Outputs: `q_parallel_MW_per_m2`, `q_parallel_limit_MW_per_m2`, `Psep_MW`
- Modes: `conservative`, `baseline`, `aggressive`
- Location: `src/engineering/heat_exhaust/divertor.py`

### Availability proxy
- Outputs: `availability`, planned/forced outage fractions
- Location: `src/availability/model.py`

### Component CAPEX proxy
- Outputs: `capex_total_MUSD` + component breakdown
- Location: `src/economics/components/stack.py`


## Auditability and validity

Each proxy model has a **model card** (`src/model_cards/*.yaml`) that records assumptions, equations, and (optionally) declared **validity ranges**. During evaluation, SHAMS stores:

- `outputs.model_cards` (ID, version, hash)
- `outputs.model_cards_validity` (per-card in-range / out-of-range status)

These are used by regression structural diffs (severity classification) and are included in the PDF summary.
