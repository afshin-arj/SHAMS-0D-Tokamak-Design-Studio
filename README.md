# SHAMS — Tokamak 0-D Design Studio

**SHAMS** is a **feasibility-authoritative tokamak system code and governance platform**.  
It is designed to determine:

- what tokamak designs are physically admissible,
- why feasibility breaks (dominant mechanism attribution),
- where design space is robust, fragile, mirage, or empty,
- and how confident one can be in any conclusion.

SHAMS explicitly allows:
- infeasible designs,
- empty regions of design space,
- and **NO-SOLUTION** as a valid scientific outcome.

SHAMS explicitly does **not**:
- optimize *inside* physics truth,
- hide infeasibility via solver convergence,
- negotiate constraints using penalties or smoothing.

All physics is evaluated using a **frozen, deterministic, algebraic evaluator**:  
same inputs → same outputs, with full auditability.

---

## What Has Been Implemented

As of **v326.1**, SHAMS includes:

### Physics & Truth (Frozen)
- Frozen deterministic 0-D plasma physics with conservative scalings  
- 1.5D profile proxy bundle (temperature, density, shear, pedestal width)  
- Explicit constraint governance (hard / diagnostic / ignored)  
- Exhaust & divertor authority (heat flux, detachment, impurity radiation)  
- Magnet authority (HTS margins, stress, envelopes)  
- Control & stability authority (VS, RWM, PF, CS budgets)  
- Neutronics & materials authority (domain-tightened)  
- Fuel cycle & tritium authority  
- Plant power ledger (explicit energy accounting)

### Exploration, Optimization & Interpretation (Firewalled)
- Intent-to-Machine compiler  
- Deterministic scan lab  
- Robust Pareto analysis (worst-phase / worst-corner)  
- Design family clustering and regime maps  
- **Certified external optimization orchestration** (NSGA-II, CMA-ES, BO, etc.)  
- Objective contracts and optimizer evidence dossiers  
- Feasible-first surrogate acceleration (non-authoritative)  
- Mirage detection (optimistic vs robust lanes)  
- One-click reviewer-ready evidence packs with hash manifests  

The UI is **Streamlit-only**, deck-based, verdict-first, and expert-oriented, with full inter-panel interoperability and deterministic replay.

---

## Optimization Philosophy (Important)

SHAMS **does support optimization**, but **never inside physics truth**.

Optimization in SHAMS is:
- **external** (runs outside the evaluator),
- **firewalled** (cannot mutate physics, constraints, or closures),
- **contract-governed** (explicit objectives, bounds, and feasibility rules),
- **evidence-integrated** (every optimizer result is traceable and auditable).

Optimizers explore the design space that SHAMS defines as admissible;  
they **cannot negotiate constraints or force convergence**.

This allows SHAMS to:
- compete directly with PROCESS-style optimization workflows,
- while preserving determinism, feasibility authority, and reviewer safety.

---

## SHAMS vs PROCESS (High-Level)

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Core role | **Feasibility authority + optimization governor** | Design optimizer |
| Evaluator | Frozen, algebraic, deterministic | Coupled nonlinear solvers |
| Iteration / solvers | **Not allowed in truth** | Central |
| Optimization | **External, firewalled, evidence-checked** | Internal |
| Constraint handling | Explicit, never negotiated | Penalties / relaxation |
| Failure reporting | **First-class outcome** | Typically avoided |
| Robustness | Explicit, worst-case | Nominal |
| Auditability | **Replayable, hash-manifested** | Limited |

**PROCESS** answers:  
> *“What design optimizes a chosen objective, assuming constraints can be negotiated?”*

**SHAMS** answers:  
> *“Which designs are physically admissible, how robust they are, and—if optimized externally—why the optimizer succeeded or failed.”*

SHAMS can therefore **complement or retire PROCESS** in roles requiring feasibility authority, robustness assessment, and regulatory-grade reasoning.

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

## Contact

For technical questions, reviews, or collaboration inquiries:

**Dr. Afshin Arjhangmehr**  
📧 **ms.arjangmehr@gmail.com**

((I will try to answer in short))
