# SHAMS — Tokamak 0‑D Design Studio

SHAMS is a **feasibility-authoritative tokamak system code and governance platform**.
It is designed to answer:

- **What tokamak designs are physically admissible**
- **Why feasibility breaks** (dominant mechanism attribution)
- **Where design space is robust, fragile, mirage, or empty**
- **How confident one can be** in any conclusion (contracts + evidence)

SHAMS is **not** an internal optimizer. Optimization is **external-only** and firewalled.

## Core laws (non-negotiable)

1. **Frozen Truth**
   - Deterministic, algebraic evaluator
   - **No Newton solvers, no iteration, no hidden relaxation or smoothing**
   - Same inputs → same outputs (bitwise reproducible)

2. **Separation of concerns**
   - Truth (evaluator) ≠ Exploration (scans/trade) ≠ Optimization (external) ≠ Interpretation (governance)

3. **Feasibility first**
   - Constraints are explicit and classified: **hard / diagnostic / ignored**
   - Violations are **reported, never negotiated**

4. **Audit & reviewer safety**
   - Replayable outputs
   - Hash-manifested evidence packs
   - Authority-tier visibility

See: `GOVERNANCE.md` and `NON_OPTIMIZER_MANIFESTO.md`.

## What SHAMS includes (v326.1)

- Frozen deterministic evaluator + conservative 0‑D physics
- 1.5D profile proxy bundle (α_T, α_n, shear, pedestal width)
- Robust Pareto Lab (worst-phase / worst-corner) + surrogate acceleration (non-authoritative)
- Certified Search (budgeted, deterministic) + repair suggestions
- Authorities: Exhaust/Divertor, Magnets, Control & Stability, Disruption risk tiering, Impurity radiation & detachment, Neutronics/Materials, Fuel cycle, Plant power ledger
- Reviewer artifacts: One‑click reviewer pack builder, evidence ZIPs + SHA‑256 manifests
- UI governance: deck-based, verdict-first Streamlit UI
- UI wiring audits: **Interoperability contract validator**

## Quickstart (local)

### 1) Create a Python environment
Python 3.10+ recommended.

### 2) Install requirements
```bash
pip install -r requirements.txt
```

### 3) Run the UI
- Windows: `run_ui.cmd`
- Linux/macOS: `./run_ui.sh`

The launchers enforce hygiene (`PYTHONDONTWRITEBYTECODE=1` + cleaning).

## Repository structure (high level)

- `src/`, `physics/`, `constraints/`, `models/`, `profiles/`: **Frozen truth and authoritative subsystems**
- `tools/`, `clients/`: exploration and external optimizer interfaces (firewalled)
- `ui/`: Streamlit decks and governance UI
- `verification/`, `validation/`, `tests/`: harnesses and gatechecks

## License

Apache-2.0 (see `LICENSE`). Attribution: © 2026 Afshin Arjhangmehr.

## Citation

See `CITATION.cff`.

