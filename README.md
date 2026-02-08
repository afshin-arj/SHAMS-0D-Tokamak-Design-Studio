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
- **NO-SOLUTION** as a valid scientific outcome.

SHAMS explicitly does **not**:
- optimize *inside* physics truth,
- hide infeasibility via solver convergence,
- negotiate constraints using penalties, smoothing, or relaxation.

All physics is evaluated using a **frozen, deterministic, algebraic evaluator**:  
same inputs → same outputs, with full auditability.

---

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
| Numerical transparency | One-pass, visible evaluation | Convergence path opaque |

---

### 3. Constraint Handling & Limits

| Topic | SHAMS | PROCESS |
|------|-------|---------|
| Constraint classification | **Hard / Diagnostic / Ignored (explicit)** | Implicit via penalties |
| Constraint negotiation | **Not allowed** | Common |
| Constraint violation | Reported and preserved | Reduced until convergence |
| Dominant failure mechanism | **Explicitly identified** | Often obscured |
| Plasma limits (β, q, Greenwald) | Conservative envelopes | Often softened |
| Engineering margins | **First-class citizens** | Tunable |

---

### 4. Plasma Physics Modeling

| Area | SHAMS | PROCESS |
|----|-------|---------|
| Core confinement | 0-D scalings (conservative) | 0-D scalings |
| Profiles | **1.5D proxy bundle (T, n, shear, pedestal)** | Parametric / implicit |
| Transport solvers | **Not implemented (by design)** | Not true transport either |
| Burn physics | Deterministic α-heating balance | Solver-coupled |
| Radiation | **Explicit impurity & detachment authority** | Simplified |
| Edge / SOL | **Exhaust authority with detachment logic** | Simplified limits |

---

### 5. Engineering Authorities

| Subsystem | SHAMS | PROCESS |
|---------|-------|---------|
| Magnets | **HTS margins, stress envelopes** | Parametric coil models |
| Exhaust / divertor | **Authority-grade heat flux & detachment** | Approximate |
| Control & stability | **VS, RWM, PF, CS budgets** | Largely absent |
| Disruptions | **Deterministic risk tiering** | Minimal |
| Neutronics | **Domain-tightened authority** | Approximate |
| Fuel cycle / tritium | **Explicit authority** | Simplified |
| Plant power ledger | **Explicit energy accounting** | Aggregated |

---

### 6. Optimization Capability (Critical Distinction)

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Internal optimization | **Forbidden** | Core feature |
| External optimization | **Yes (firewalled)** | N/A |
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
| Failure explanation | **Narrative + mechanism** | Limited |

---

### 8. Governance, Audit & Review

| Feature | SHAMS | PROCESS |
|------|-------|---------|
| Audit trail | **Hash-manifested evidence packs** | None |
| Replayability | **Guaranteed** | Not guaranteed |
| Reviewer artifacts | **One-click reviewer pack** | Manual |
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
| Inter-panel interoperability | Canonical promotion paths | N/A |

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

## Contact

For technical questions, reviews, or collaboration inquiries:

**Afshin Arjhangmehr**  
📧 **ms.arjangmehr@gmail.com**
