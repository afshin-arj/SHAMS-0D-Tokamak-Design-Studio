# Constitutional Benchmarks — Tokamak Constitutional Atlas (v256.0+)

SHAMS benchmarks are **feasibility-authoritative** and **deterministic**.

The **Tokamak Constitutional Atlas** evaluates *famous tokamak presets* under an explicit **Design Intent**:

- **Research** intent: reactor-only closures are diagnostic/ignored (by constitution)
- **Reactor** intent: plant closures are required (by constitution)

## What it is (and is not)

- ✅ Preset-driven (no tuning, no sliders)
- ✅ Frozen evaluator (Point Designer truth)
- ✅ Intent-aware feasibility semantics
- ✅ Deterministic evidence capsules (JSON + SHA-256 stamp)

- ❌ Not a parameter-fit “reproduction”
- ❌ Not a ranking of machines
- ❌ Not an optimizer

## UI location

**Benchmarks → Constitutional Benchmarks → Tokamak Constitutional Atlas**

Workflow:
1. Select a **preset** (JET, DIII-D, EAST, KSTAR, JT-60SA, ITER, SPARC, ARC, DEMO, …)
2. Toggle **Intent** (Research / Reactor)
3. Review:
   - Verdict (PASS / PASS+DIAG / FAIL)
   - Constitution diff (selected intent → preset native intent semantics)
   - Local envelope & fragility (small deterministic neighborhood grid)
   - Evidence capsule download

## Evidence capsule schema

`tokamak_constitutional_atlas_result.v1`

Includes:
- preset key/label
- selected and native intent constitutions
- constitution diff (clause-level)
- Point Designer run outputs and constraint ledger
- stable SHA-256 stamp for audit trails
