# Reactor Design Forge v203 — Freeze-Grade Specification

Author: © 2026 Afshin Arjhangmehr
Tone: Option B (high-field bold, forge/foundry vibe)

## 1) Role and Epistemic Contract
Reactor Design Forge is a **candidate machine foundry**. It accelerates honest exploration but never claims authority.

**Hard guarantees**
- Frozen truth comes from **Point Designer** only (physics + constraints).
- Forge never changes evaluator physics, constraints, or Design Intent policy.
- No hidden relaxations, no implicit penalties, no recommendation engine.
- Every candidate is auditable: inputs, outputs, constraints, margins, provenance.

**Non-guarantees (explicit limits)**
- Forge does not guarantee global optimality.
- Surrogates are proposal-only; the frozen evaluator always arbitrates.

## 2) Naming
Mode name: **Reactor Design Forge**

Primary subpanels (fusion-expert labels)
- **Archive Bay** — diverse candidate archive
- **Machine Dossier** — deep inspection (Truth/Closure/Margins/Reality/Economics)
- **Resistance Brief** — why the region pushes back
- **Conflict Atlas** — descriptive co-occurrence of limiting constraints
- **Boundary Navigator** — local feasibility boundary instrument
- **Casebook** — program-style declared cases
- **Audit Pack** — capsule + report exports

## 3) Core Features (PROCESS-independence tier)
### 3.1 Closure Console (always computed, explicit)
For every evaluated candidate, compute a Closure Bundle:
- gross electric, recirculating power, net electric
- recirc breakdown placeholders (cryo / CD / aux / BOP) when available
- economics envelopes: Optimistic / Nominal / Conservative (explicit scalings)

### 3.2 Reality Gates (declared, toggleable)
Provide PASS/FAIL gates derived from existing constraints and closure:
- stress, heat flux, HTS margin, TBR, q95
- net electric gate when intent is Power Reactor

### 3.3 Margin Ledger (no scalar score)
Provide an explicit constraint margin table:
- ordered by tightness
- min signed margin
- tight constraints list

### 3.4 Casebook-first workflow
A **Case** is an explicit contract:
- intent
- lens
- bounds
- budgets
- closure/economics envelope selection
- reality gates enabled set

Casebook outputs are comparable but not ranked.

### 3.5 Report Pack (PROCESS-recognizable, audit-clean)
Exports for a candidate:
- JSON report pack (authoritative content)
- Markdown summary
- CSV flattened key/value table

## 4) Artifacts and Schemas
- `closure_bundle.schema`: `shams.reactor_design_forge.closure_bundle.v1`
- `reality_gates.schema`: `shams.reactor_design_forge.reality_gates.v1`
- `margin_budget.schema`: `shams.reactor_design_forge.margin_budget.v1`
- `report_pack_export.schema`: `shams.reactor_design_forge.report_pack_export.v1`

All are included in the Optimization Run Capsule v2 when available.

## 5) Prohibitions (Freeze-grade)
- No “best point” recommendation language in UI.
- No hidden penalties in feasibility logic.
- No automatic apply-to-truth.
- No mutation of constraints or physics.

## 6) Regression and Determinism
- Runs are seeded.
- Artifacts include evaluator hash + repo fingerprint.
- Capsule replay must not change truth outputs.
