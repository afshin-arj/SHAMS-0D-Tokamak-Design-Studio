# SHAMS — Scan Lab Freeze Contract

**Status:** Freeze-ready contract (Scan Schema v1)

**Author:** © 2026 Afshin Arjhangmehr

**North Star:** *Point Designer defines truth. Scan Lab maps truth.*

---

## 1. Purpose

Scan Lab is a **0‑D design space cartography tool**. It exists to answer questions like:

- *Which constraint limits me where?*
- *What fails first? In what order?*
- *Where are the cliffs and regime boundaries?*
- *How does Research vs Reactor intent change acceptance?*

Scan Lab is **not** a solver, and it must never mutate the authoritative 0‑D physics.

---

## 2. What Scan Lab is

Scan Lab performs **pure evaluation** of the frozen Point Designer model at a set of points (grid, sparse, or path).
From those evaluations it derives deterministic maps:

- Constraint‑dominance cartography
- First‑failure topology / failure order statistics
- Intent‑split feasibility (Research vs Reactor) using the frozen intent policy
- Local robustness labels (Robust / Balanced / Brittle / Knife‑edge)
- Structured narrative summaries (derived from statistics only)

---

## 3. What Scan Lab is not

Scan Lab must never:

- Optimize, search, rank, or recommend designs
- Relax constraints or change thresholds
- Change Point Designer physics, constraints, or convergence logic
- Hide infeasible points or smooth feasibility boundaries

If a feature would cause Scan Lab to "choose" a design, it belongs in **Systems Mode** (or a future Lab), not Scan.

---

## 4. Frozen interfaces (post-freeze stability)

The following are **frozen** when Scan Lab is declared frozen:

- **Scan artifact schema** (`scan_schema_version = 1`) and the upgrader contract
- Deterministic **reason codes** (no free‑text drift)
- Dominance rule (worst margin among blocking constraints)
- Robustness labels and thresholds
- Narrative generation rules (ordering, phrasing templates, statistics)
- Constraint color mapping (constraint → color key)

Post‑freeze changes are limited to:

- Bug fixes that preserve semantics
- Performance improvements that preserve outputs
- Documentation and wording clarifications

---

## 5. Determinism & replay

For a fixed:

- Base inputs
- Scan settings (axes, bounds, resolution)
- Intent set
- Seed (if applicable)

Scan Lab must produce:

- Identical JSON artifacts after upgrade-to-v1 normalization
- Stable hashes for key report sections

PDF/PNG exports may include timestamps, but the underlying **report hashes** must be stable.

---

## 6. QA and regression

Scan Lab ships with **Golden scans** used for:

- Teaching / onboarding
- Deterministic regression testing
- Demonstration

Golden scans must be runnable headlessly and must validate:

- Artifact schema correctness (v1)
- Dominance distribution stability within tolerance
- Topology flags stability
- Atlas export is exactly 10 pages and non‑empty
