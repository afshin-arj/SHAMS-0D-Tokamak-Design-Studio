# SHAMS — Tokamak 0-D Design Studio

**Version:** v418.1.0  
**Posture:** Feasibility-authoritative · Frozen deterministic truth · NO-SOLUTION is valid science

---

## What SHAMS is

**SHAMS** (*Systematic Hot-ion Analysis for Magnetic confinement Systems*) is a **tokamak 0-D design studio and governance platform** for fusion engineers, program reviewers, and researchers who need to know:

- which designs are **physically admissible** under explicit constraints,
- **why** feasibility breaks (dominant mechanism, not solver noise),
- where design space is **robust, fragile, mirage, or empty**,
- and how **confident** a conclusion is given declared model authority.

SHAMS is deliberately **not** an optimizer inside physics truth. It is a **single-pass, deterministic evaluator** with explicit hard / diagnostic / ignored constraints, full artifact provenance, and reviewer-grade export paths.

> **Same inputs → same outputs.** No hidden iteration, smoothing, or penalty negotiation in frozen truth (L0).

---

## Why the community should care

| Question | Typical system codes | SHAMS |
|----------|---------------------|-------|
| What if the design is infeasible? | Often obscured by solver failure | **Reported, attributed, preserved** |
| Can I replay this for a review? | Ad hoc | **Hash-manifested artifacts & packs** |
| Does empty design space exist? | Discouraged implicitly | **Explicit NO-SOLUTION atlas** |
| Can an optimizer change physics? | Sometimes coupled | **Firewalled — optimizers propose inputs only** |

SHAMS complements codes like **PROCESS** where you need **feasibility authority** and auditability rather than negotiated convergence to an objective.

---

## Studio UI — NiceGUI (recommended)

The primary interface is the **NiceGUI design studio** — a verdict-first, deck-based workflow aligned with how fusion experts actually study a machine:

| Step | Deck | Purpose |
|------|------|---------|
| 1 | **Point Designer** | Anchor one operating point; read feasibility verdict |
| 2 | **Scan Lab** | Map feasible regions (cartography) |
| 3 | **Systems Mode** | Integrated plant / systems closure |
| 4 | **Compare** | Baseline vs scenario artifact diffs |
| 5 | **Pareto Lab** | Nondominated feasible frontiers |
| 6 | **Trade Study Studio** | Certified trade studies & robust lanes |
| 7 | **Reactor Design Forge** | Concept families, casebook, dossiers |
| 8 | **Publication Benchmarks** | Constitutional atlas, reviewer packs |
| 9 | **System Suite** | Batch campaigns |
| 10 | **Control Room** | Governance, provenance, export, audit |

**Launch (Windows):**
```cmd
run_ui_nicegui.cmd
```

**Launch (Linux / macOS):**
```bash
./run_ui_nicegui.sh
```

**Launch (Python):**
```bash
cd SHAMS-0D
pip install -r requirements.txt
python ui_nicegui/app.py
```

The legacy Streamlit shell (`run_ui.cmd`) remains for compatibility but **redirects fully ported decks** to NiceGUI.

---

## Quick start (first evaluation)

```bash
git clone https://github.com/afshin-arj/SHAMS-0D-Tokamak-Design-Studio.git
cd SHAMS-0D-Tokamak-Design-Studio
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_smoke.py -q
run_ui_nicegui.cmd    # or ./run_ui_nicegui.sh
```

1. Open **Point Designer** → configure geometry & plasma → **Evaluate**.  
2. If feasible, explore **Scan Lab** or **Systems Mode**.  
3. Use **Compare** / **Pareto Lab** for design decisions.  
4. Seal the study in **Control Room** (protocol, repro lock, export).

---

## Architecture

SHAMS is organized as a **layered authority stack**: one frozen physics core (L0), read-only overlays and exports above it (L1–L4), and a **NiceGUI studio** that routes every evaluation through a single choke point. External optimizers and batch tools **propose inputs only** — SHAMS re-evaluates and records evidence.

### System overview

```mermaid
flowchart TB
  subgraph UI["NiceGUI Studio · ui_nicegui/"]
    HC[Helm Console<br/>intent · TRL · reference machines · gatecheck]
    PD[Point Designer]
    SL[Scan Lab]
    SM[Systems Mode]
    CP[Compare]
    PL[Pareto Lab]
    TS[Trade Study Studio]
    RF[Reactor Design Forge]
    PB[Publication Benchmarks]
    SS[System Suite]
    CR[Control Room]
    HC --> PD & SL & SM & CP & PL & TS & RF & PB & SS & CR
  end

  subgraph L0["L0 — Frozen truth (never mutated by UI)"]
    SCH[PointInputs schema]
    EV[Evaluator.evaluate]
    HI[hot_ion_point]
    CON[constraints hard / diagnostic / ignored]
    SCH --> EV --> HI --> CON
  end

  subgraph OUT["Immutable outputs"]
    ART[shams_run_artifact.json]
    LED[constraint_ledger]
    OVL[authority overlays post-truth]
    ART --- LED & OVL
  end

  subgraph EXT["External · firewalled"]
    OPT[NSGA-II · CMA-ES · BO · custom]
    OPT -. propose inputs only .-> EV
  end

  PD & SL & SM & CP & PL & TS & RF & SS -->|ui_evaluate| EV
  EV --> ART
  ART --> CP & PL & TS & CR & PB
  CR & PB -->|protocol · repro lock · packs| EXP[Reviewer / regulatory exports]
```

### Layer model

Higher layers **read** L0 artifacts and **write new** derived artifacts — they never rewrite physics results.

```mermaid
flowchart BT
  L4["L4 · Explainability<br/>narratives · forensics · mechanism labels"]
  L3["L3 · Mission context<br/>scenarios · design intent · TRL contracts"]
  L2["L2 · Engineering interfaces<br/>handoff packs · export adapters · cross-code parity"]
  L1["L1 · Authority & reference<br/>citation · governance · reproducibility lock"]
  L0["L0 · Frozen physics + constraints<br/>evaluator · hot_ion · NO-SOLUTION valid"]

  L4 --> L3 --> L2 --> L1 --> L0
```

| Layer | Code anchor | What it does |
|-------|-------------|--------------|
| **L0** | `src/evaluator/core.py` → `src/physics/hot_ion.py` | Single-pass deterministic evaluation; constraint ledger; run artifacts |
| **L1** | `analysis/` authority overlays, `GOVERNANCE.md` | Confidence tiers, dominance, epoch feasibility, constitutional docs |
| **L2** | `src/campaign/`, `tools/` export builders | Benchmark packs, reviewer ZIPs, licensing bundles, case decks |
| **L3** | Helm Console design contract, mission profiles | Reactor / research / pilot / HFS intent; enforcement tiering |
| **L4** | Chronicle instruments, Compare diffs, Scan interpret | Sensitivity, feasibility maps, scenario delta, local forensics |

### Expert workflow — all ten decks

Decks follow the **numbered sidebar workflow** (Helm Console → Navigation). Each deck is verdict-first; none iterates inside L0 truth.

```mermaid
flowchart LR
  subgraph P1["1 · Anchor"]
    PD2[Point Designer<br/>configure · evaluate · constraints atlas]
  end
  subgraph P2["2 · Map & close"]
    SL2[Scan Lab<br/>2D cartography · interpret · signature atlas]
    SM2[Systems Mode<br/>plant closure · feasibility map · recovery]
  end
  subgraph P3["3 · Compare & trade"]
    CP2[Compare<br/>A/B artifacts · structural diff · export]
    PL2[Pareto Lab<br/>feasible frontier · robust lanes · packs]
    TS2[Trade Study Studio<br/>frontier atlas · certification · surrogate]
  end
  subgraph P4["4 · Concepts"]
    RF2[Reactor Design Forge<br/>intent compiler · casebook · dossiers]
  end
  subgraph P5["5 · Evidence & audit"]
    PB2[Publication Benchmarks<br/>constitutional atlas · cross-code · licensing]
    SS2[System Suite<br/>phase cockpit · campaigns · UQ bounds]
    CR2[Control Room<br/>provenance · run audit · chronicle · export]
  end

  P1 --> P2 --> P3 --> P4 --> P5
  PD2 -. artifacts .-> SL2 & SM2 & CP2 & PL2
  CP2 & PL2 & TS2 -. artifacts .-> CR2 & PB2
```

### Deck feature map

| Deck | Primary tabs / sections | Key capabilities |
|------|-------------------------|------------------|
| **Point Designer** | Configure · Telemetry · Constraints · Mission | Single-point evaluate; NO-SOLUTION atlas; constraint diff dossier; overlay dashboard |
| **Scan Lab** | Setup · Cartography · Interpret · Artifact restore | 2D feasible-region maps; first-failure topology; scan atlas capsules |
| **Systems Mode** | Workflow tabs + plant authority | Integrated systems solve; power-balance diagram; feasibility heatmap; reproduce/diff |
| **Compare** | Load · Performance · Constraints · Inputs & Structure · Export | Metric/input/structural diffs; scenario delta; comparison bundles |
| **Pareto Lab** | Explore · Interpret · Audit · Publication · External | Nondominated feasible frontier; mirage filtering; optimistic vs robust lanes |
| **Trade Study Studio** | Setup · Frontier · Robust · Surrogate · Optimizer kits | Certified trade studies; interval narrowing; external optimizer handoff |
| **Reactor Design Forge** | Intent · Explore · Casebook · Archive · Dossier | 67 expert instruments; staged runs; collaboration sessions |
| **Publication Benchmarks** | Atlas · Pack · Cross-Code · Governance · Evidence | Constitutional preset atlas; reviewer/regulatory/licensing ZIPs |
| **System Suite** | Workflow + phase cockpit | Batch campaigns; mode contracts; parity suite; absolute UQ bounds |
| **Control Room** | Orient · Constitution · Provenance · Artifacts · Diagnostics · Chronicle | Run audit overlays; case deck runner; scenario delta; constraint cockpit; repro lock |

**Helm Console** (always visible in the left drawer): session posture, design contract (intent + TRL + q95/Greenwald enforcement), reference machine presets, fidelity declarations, calibration multipliers, integrity gatecheck, activity chronicle, and deck navigation.

### Evaluation choke point

Every UI path that needs physics calls **`ui_evaluate()`** → **`Evaluator.evaluate()`** → **`hot_ion_point()`**. No deck bypasses this chain.

```mermaid
sequenceDiagram
  participant User
  participant Deck as Any deck UI
  participant UI as ui_evaluate()
  participant EV as Evaluator.evaluate()
  participant HI as hot_ion_point()
  participant CON as evaluate_constraints
  participant ART as shams_run_artifact.json

  User->>Deck: configure / scan / compare / …
  Deck->>UI: PointInputs (+ origin tag)
  UI->>EV: evaluate(inputs)
  EV->>HI: frozen physics (L0)
  HI->>CON: hard / diagnostic / ignored
  CON->>ART: ledger + overlays + inputs hash
  ART-->>Deck: verdict · margins · provenance
  Note over EV,HI: Same inputs → same outputs<br/>NO-SOLUTION is a valid outcome
```

### Artifact & governance flow

Artifacts are **immutable** once written. Downstream decks consume them read-only; exports append new hashed bundles.

```mermaid
flowchart LR
  EVAL[Point / scan / systems evaluate]
  ART[(shams_run_artifact.json)]
  PROTO[study_protocol]
  REPRO[repro_lock]
  PACK[publication / reviewer pack]
  DIFF[Compare · scenario delta]
  AUDIT[Control Room run audit]

  EVAL --> ART
  ART --> PROTO & REPRO & DIFF & AUDIT
  ART --> PACK
  PROTO & REPRO --> ZIP[hashed export ZIP]
  PACK --> ZIP
```

### Repository map

| Area | Path |
|------|------|
| Frozen evaluator | `src/evaluator/` · `src/physics/hot_ion.py` |
| Constraints | `src/constraints/` · `authority_caps.json` |
| Authority overlays | `analysis/` |
| NiceGUI studio | `ui_nicegui/` (`app.py`, `decks/`, `session.py`) |
| Legacy UI (redirects) | `ui/app.py` |
| Tests & golden baselines | `tests/` · `tests/golden/` |
| Verification gate | `verification/run_verification.py` |
| Governance | `GOVERNANCE.md` · `VERSION` |

**Validation:** `pytest` · `python verification/run_verification.py`

---

## Scientific scope (honest limits)

SHAMS is a **0-D / volume-averaged / steady-state** screening studio with explicit engineering proxies (magnets, exhaust, neutronics tiers, plant ledger). It does **not** implement:

- time-domain transport solvers,
- Monte Carlo inside truth,
- internal optimization or Newton negotiation in L0.

Those belong **outside** the evaluator, with SHAMS re-evaluating every proposed input set.

---

## Latest release notes (v418.x)

- **NiceGUI studio complete** — all primary decks ported with expert workflow navigation, guided modes, and Streamlit redirects.
- Registry code-generation from `authority_caps.json`; NO-SOLUTION mechanism atlas; constraint diff dossier in Point Designer.
- H-mode scalings, ELM duty-cycle availability, tritium reactor preset; overlay dashboard refresh.

Details: `docs/patch_notes/PATCH_NOTES_v418.md`

---

## SHAMS vs PROCESS (one paragraph)

**PROCESS** asks: *what design optimizes my objective if constraints can be negotiated?*  
**SHAMS** asks: *which tokamak designs are admissible, how robust are they, why do others fail, and what evidence supports the claim?*

For the full comparison table, see the [extended comparison section](#extended-comparison-shams-vs-process) below.

---

## Contributing & governance

- Physics / constraint changes: explicit request + versioning (`GOVERNANCE.md`)
- Additive UI, schemas, docs: welcome without altering L0 behavior
- Run `pytest` and `python verification/run_verification.py` before PRs

---

## Contact

**Dr. Afshin Arjhangmehr**  
📧 ms.arjangmehr@gmail.com

---

## Extended comparison: SHAMS vs PROCESS

### 1. Purpose & Philosophy

| Dimension | SHAMS | PROCESS |
|---------|-------|---------|
| Primary role | **Feasibility authority & governance system** | Design optimization system |
| Core question | *What machines can physically exist, and why others cannot?* | *What machine optimizes a chosen objective?* |
| Treatment of failure | **First-class scientific result** | Avoided if possible |
| Empty design space | **Explicitly allowed** | Implicitly discouraged |
| Scientific posture | Constraint-first, mechanism-explicit | Objective-first, solver-driven |
| Intended use | Review, feasibility authority, governance | Parametric design optimization |

### 2. Numerical & Algorithmic Discipline

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Evaluator type | **Frozen deterministic algebraic evaluator** | Coupled nonlinear solver system |
| Iteration | **Forbidden in L0 truth** | Central |
| Determinism | **Bitwise reproducible** | Solver-path dependent |
| Same inputs → same outputs | **Guaranteed** | Not guaranteed |

### 3. Constraint Handling

| Topic | SHAMS | PROCESS |
|------|-------|---------|
| Constraint classification | **Hard / Diagnostic / Ignored (explicit)** | Implicit via penalties |
| Constraint negotiation | **Not allowed in truth** | Common |
| Dominant failure mechanism | **Explicitly identified** | Often obscured |

### 4. Optimization (critical distinction)

| Aspect | SHAMS | PROCESS |
|------|-------|---------|
| Internal optimization | **Forbidden in L0** | Core feature |
| External optimization | **Yes (certified & firewalled)** | N/A |
| Feasibility enforcement | **Absolute** | Negotiable |

### 5. Governance & Review

| Feature | SHAMS | PROCESS |
|------|-------|---------|
| Audit trail | **Hash-manifested evidence packs** | None |
| Replayability | **Guaranteed** | Not guaranteed |
| Reviewer artifacts | **One-click reviewer packs** | Manual |

---

## License

See repository license file. Cite SHAMS version and artifact hashes when publishing results derived from this studio.
