# SHAMS — Tokamak 0-D Design Studio

**Current version:** v415.0.0 — Studio audit: constraint ledger parity, Robust Pareto Evaluator choke point

**SHAMS** is a **feasibility-authoritative tokamak system code and governance platform**.

It is designed to determine:

- what tokamak designs are physically admissible,
- why feasibility breaks (explicit dominant mechanism attribution),
- where design space is robust, fragile, mirage, or empty,
- and how confident one can be in any conclusion.

SHAMS explicitly allows:
- infeasible designs,
- empty regions of design space,
- **NO-SOLUTION** as a valid scientific outcome.

SHAMS explicitly does **not**:
- optimize *inside* physics truth,
- hide infeasibility via solver convergence,
- negotiate constraints using penalties, smoothing, relaxation, or weighting.

All physics is evaluated using a **frozen, deterministic, algebraic evaluator**:  
**same inputs → same outputs**, with full auditability and replayability.

---

## Latest upgrade — v415.0.0 (Studio Improvement Audit)

- Constraint ledger parity: v397 q0/bootstrap, v398 stability, v399 impurity caps, v403 granular neutronics.
- Robust Pareto Lab routes through Evaluator choke point; timezone-aware UTC stamps.
- See `docs/patch_notes/PATCH_NOTES_v415.md` and `docs/validation/reports/studio_audit_report_20260703.md`.

## Previous upgrade — v414.0.0 (Top-5 Audit Findings)

- **PROPOSAL-010:** v396/v397/v384/v407 caps mirrored across constraint pipelines.
- **PROPOSAL-011:** Governance overlay `*_error` surfacing in `hot_ion.py`.
- **PROPOSAL-012:** Import fallbacks for overlays and certification modules.
- Certification import smoke tests. See `docs/patch_notes/PATCH_NOTES_v414.md`.

## Prior upgrade — v413.0.0 (Post-v412 Audit Safe Fixes)

- Constraint `severity` respected in Monte Carlo / nudge feasibility paths.
- v401/v403 min-margin enforcement in `evaluate_constraints`; v403 fragile margin wired in ledger.
- Certification v374 smoke test. See `docs/patch_notes/PATCH_NOTES_v413.md`.

## Prior upgrade — v412.0.0 (UI Choke Point + Constraint API)

- **PROPOSAL-008:** UI point evaluation routed through `Evaluator.evaluate()` via `_ui_evaluate()` (one golden-regen bypass documented).
- **PROPOSAL-009:** `LedgerConstraint` vs `GovernanceConstraint` with adapters and unified `constraints` public API.
- See `docs/patch_notes/PATCH_NOTES_v412.md`.

## Prior upgrade — v411.0.0 (v402 Dominance Pipeline)

- **PROPOSAL-007:** `hot_ion.py` flat import fallback for `authority_dominance_v402` — default-ON overlay now merges in standard eval path.
- Additive v402 dominance keys in golden baselines. See `docs/patch_notes/PATCH_NOTES_v411.md`.

## Prior upgrade — v410.0.0 (Governance & Confinement Consistency)

- **PROPOSAL-002:** `betaN_proxy` constraint wiring in `constraints.py`
- **PROPOSAL-003:** v396 envelope prefers `P_SOL_MW` for τE scalings
- **PROPOSAL-004:** ITER89-P R exponent 1.5 → 1.2 (published scaling)
- **PROPOSAL-005:** v398 evaluated after v397 merge + CS flux fields
- **PROPOSAL-006:** `confinement_mult` applied consistently to `H_required`
- Golden/benchmark baselines regenerated. See `docs/patch_notes/PATCH_NOTES_v410.md`.

## Prior upgrade — v409.0.0 (Thermal Stored Energy Prefactor Correction)

- **L0 frozen-truth fix:** `W_J = 1.5 × n_e (T_i + T_e) V` (was 3.0 — double-counting bug).
- W-dependent metrics (`W_MJ`, `tauE_s`, `H98`, `H_required`) scale ~×0.5; power balance unchanged.
- Golden, benchmark, and validation baselines regenerated. See `docs/patch_notes/PATCH_NOTES_v409.md`.

## Prior upgrade — v408.0.0 (Nuclear Dataset Intake & Provenance Builder)

- Adds a **firewalled intake pathway** for external multi-group screening datasets.
- Supports **JSON dataset import** (full schema) and **metadata JSON + sigma-removal CSV** intake.
- Enforces strict validation (schema, group lengths, spectrum normalization), and pins every dataset by **SHA-256**.
- Writes optional deterministic **dataset evidence cards** into `data/nuclear_datasets/` for reviewer packs.
- UI provides an upload → validate → save workflow; v407 selectors now list **all** registry datasets.


v405 upgrades SHAMS' **external-to-truth exploration** layer to a reviewer-grade, feasibility-first frontier workflow:

- **Feasible-first Pareto exploration** (multi-objective, nondominated frontier extraction)
- **Authority-aware ranking context** per candidate via the global dominance overlay (v402)
- **Optimistic vs Robust lane separation** using deterministic interval contracts (no Monte Carlo)
- **Mirage filtering** (lane-based) and explicit mirage flags surfaced in the UI
- **Per-frontier-candidate evidence pack export** (nominal run artifact + lane contract artifacts)

This remains strictly outside frozen truth: it is a deterministic, budgeted candidate generator + verifier (not an optimizer).

## SHAMS vs PROCESS — Complete Comparison

### 1. Purpose & Philosophy

| Dimension | SHAMS | PROCESS |
|---------|-------|---------|
| Primary role | **Feasibility authority & governance system** | Design optimization system |
| Core question | *What machines can physically exist, and why others cannot?* | *What machine optimizes a chosen objective?* |
| Treatment of failure | **First-class scientific result** | Avoided if possible |
| Empty design space | **Explicitly allowed** | Implicitly discouraged |
| Scientific posture | Constraint-first, mechanism-explicit | Objective-first, solver-driven |
| Intended use | Review, feasibility authority, governance | Parametric design optimization |

---

### 2. Numerical & Algorithmic Discipline

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Evaluator type | **Frozen deterministic algebraic evaluator** | Coupled nonlinear solver system |
| Iteration | **Forbidden** | Central |
| Newton / relaxation solvers | **Not allowed** | Required |
| Hidden smoothing | **Explicitly forbidden** | Common |
| Determinism | **Bitwise reproducible** | Solver-path dependent |
| Same inputs → same outputs | **Guaranteed** | Not guaranteed |
| Numerical transparency | Single-pass, explicit evaluation | Convergence path opaque |

---

### 3. Constraint Handling & Limits

| Topic | SHAMS | PROCESS |
|------|-------|---------|
| Constraint classification | **Hard / Diagnostic / Ignored (explicit)** | Implicit via penalties |
| Constraint negotiation | **Not allowed** | Common |
| Constraint violation | Reported, preserved, attributed | Reduced until convergence |
| Dominant failure mechanism | **Explicitly identified** | Often obscured |
| Plasma limits (β, q, Greenwald, density) | Conservative envelopes | Often softened |
| Engineering margins | **First-class citizens** | Tunable |

---

### 4. Plasma Physics Modeling

| Area | SHAMS | PROCESS |
|----|-------|---------|
| Core confinement | 0-D empirical scalings (conservative) | 0-D scalings |
| Profiles | **1.5D proxy bundle** (T, n, shear, pedestal width) | Parametric / implicit |
| Transport solvers | **Not implemented (by design)** | Not true transport either |
| Burn physics | Deterministic α-heating balance | Solver-coupled |
| Radiation | **Explicit impurity radiation & detachment authority** | Simplified |
| Edge / SOL | **Exhaust authority with detachment logic** | Simplified limits |

---

### 5. Engineering Authorities (Explicitly Separated)

| Subsystem | SHAMS | PROCESS |
|---------|-------|---------|
| Magnet technology | **Explicitly separated HTS / LTS / resistive coils** | Generic coil models |
| Magnet margins | **B–T–J envelopes, stress limits, quench proxies** | Parametric |
| Structural stress | **Envelope-governed** | Simplified |
| Exhaust / divertor | **Authority-grade heat flux & detachment** | Approximate |
| Control & stability | **VS, RWM, PF, CS budgets** | Largely absent |
| Disruptions | **Deterministic risk tiering (non-predictive)** | Minimal |
| Neutronics & materials | **Domain-tightened authority + tiered contract governance (v401)** | Approximate |
| Fuel cycle / tritium | **Explicit authority** | Simplified |
| Plant power ledger | **Explicit energy accounting** | Aggregated |

---

### 6. Optimization Capability (Critical Distinction)

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Internal optimization | **Forbidden** | Core feature |
| External optimization | **Yes (certified & firewalled)** | N/A |
| Optimizer influence on physics | **Impossible by construction** | Total |
| Supported optimizers | NSGA-II, CMA-ES, BO, custom | Built-in |
| Objective contracts | **Explicit, versioned** | Implicit |
| Optimizer evidence | **Hash-manifested dossiers** | Not native |
| Feasibility enforcement | **Absolute** | Negotiable |

> SHAMS **can compete directly with PROCESS-style optimization**  
> while preserving frozen truth, determinism, and feasibility authority.

---

### 7. Robustness, Exploration & Interpretation

| Feature | SHAMS | PROCESS |
|------|-------|---------|
| Deterministic scans | Yes | Limited |
| Robust Pareto (worst-case) | **Yes** | Nominal |
| Mirage detection | **Yes (optimistic vs robust lanes)** | No |
| Design families | **Explicit clustering & narratives** | No |
| Regime maps | **Mechanism-labeled** | No |
| Failure explanation | **Narrative + mechanism attribution** | Limited |

---

### 8. Governance, Audit & Review

| Feature | SHAMS | PROCESS |
|------|-------|---------|
| Audit trail | **Hash-manifested evidence packs** | None |
| Replayability | **Guaranteed** | Not guaranteed |
| Reviewer artifacts | **One-click reviewer packs** | Manual |
| Assumption visibility | Explicit | Often implicit |
| Regulatory posture | **Review-ready** | Research-grade |

---

### 9. User Interface & Human Factors

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| UI paradigm | **Streamlit, deck-based, verdict-first** | Input files |
| Scroll walls | **Forbidden** | Common |
| Expert guidance | Scope cards per mode | None |
| Phantom features | **Impossible by rule** | Possible |
| Inter-panel interoperability | **Canonical promotion paths** | N/A |

---

## Bottom Line

**PROCESS** answers:  
> *“What design optimizes my chosen objective, assuming constraints can be negotiated?”*

**SHAMS** answers:  
> *“Which tokamak designs are physically admissible, how robust they are, why others fail, and—if optimized externally—why the optimizer succeeded or failed.”*

SHAMS can therefore **complement or retire PROCESS** in roles requiring:
- feasibility authority,
- robustness assessment,
- auditability,
- and regulatory-grade reasoning.

---

## Scope & Limitations (By Design)

SHAMS intentionally does **not** implement:
- time-domain physics,
- transport solvers,
- Monte Carlo methods,
- probabilistic disruption prediction,
- internal optimization or solver-based negotiation.

All such capabilities must remain **external and non-authoritative**.

---

---

## Installation & Quick Start

SHAMS is designed to be **easy to run locally** with a clean, deterministic setup.
No system-wide installation is required.

### Prerequisites
- **Python 3.10+** (3.10 or 3.11 recommended)
- **Git**
- Internet connection (for first-time dependency install only)

SHAMS runs on **Windows, Linux, and macOS**.

---

### 1. Clone the Repository

```bash
git clone https://github.com/afshin-arj/SHAMS-0D-Tokamak-Design-Studio.git
cd SHAMS-0D-Tokamak-Design-Studio
```

### 2. Create a Python Virtual Environment (Recommended)

Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch SHAMS (UI)

Windows
```bash
run_ui.cmd
```

Linux / macOS
```bash
./run_ui.sh
```

The SHAMS UI will open automatically in your web browser.

## Usage Notes:
- SHAMS executes no solvers, no iteration, and no hidden optimization.
- All evaluations are deterministic and replayable.
- External optimizers (if used) are firewalled and cannot modify physics truth.
- Failed designs and NO-SOLUTION outcomes are expected and meaningful.


## Contact

For technical questions, reviews, or collaboration inquiries:

**Dr. Afshin Arjhangmehr**  
📧 **ms.arjangmehr@gmail.com**
