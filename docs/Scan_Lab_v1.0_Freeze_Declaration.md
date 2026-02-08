# SHAMS Scan Lab v1.0 — Freeze Declaration

**Software:** SHAMS / Tokamak 0‑D Design Studio  
**Component:** Scan Lab (Cartography & Insight)  
**Status:** **Frozen — v1.0**  
**Author:** © 2026 Afshin Arjhangmehr

## Purpose
Scan Lab is the cartography and insight mode of SHAMS. It maps the structure of the frozen 0‑D design space using the **Point Designer** evaluator as the authoritative source of truth.

## Freeze boundary
The following are frozen and must remain stable across all v1.0 patch releases:

1. **Truth boundary**
   - Scan Lab must not change Point Designer physics, constraints, or policy.
   - Scan Lab must not introduce hidden relaxations.

2. **Non‑goal boundary**
   - Scan Lab is not an optimizer.
   - Scan Lab does not recommend or auto-apply designs.

3. **Determinism & replay**
   - Given identical baseline inputs, axes, ranges, resolution, and intent lenses, Scan Lab must produce identical scan artifacts (up to harmless metadata such as timestamps).
   - All runs must be replayable from their recorded artifacts.

4. **Visual semantics**
   - Dominance map categorical meaning is frozen (each cell shows the dominant *blocking* constraint under the selected intent lens).
   - Robustness labels and first-failure semantics remain meaning-stable.

## Included capabilities (v1.0)
Scan Lab v1.0 includes:
- Constraint-dominance cartography in a user-selected 2‑D plane.
- Intent-split evaluation (Research vs Reactor) without changing evaluator truth.
- First-failure / dominance ranking summaries and plain-language narrative text.
- Robustness classification (Robust / Balanced / Brittle / Knife-edge).
- Topology cues (disconnected islands, holes) and intentional empty-region messaging.
- Reproducible exports:
  - Scan artifact JSON (schema v1)
  - Report JSON and points CSV
  - Signature atlas / summary PDFs where available

## Excluded changes after freeze
After this declaration, the following are not allowed without a major version bump:
- Changing the Point Designer evaluator or constraint definitions as used by Scan Lab.
- Changing artifact schema v1 in a breaking way.
- Changing the semantic meaning of dominance, feasibility, or robustness categories.
- Adding optimization, auto-relaxation, or auto-application behavior.

## Allowed changes after freeze
Allowed changes are strictly presentation and stability fixes:
- Micro-level UI clarity improvements (text, ordering, visual grouping) that do not change meaning.
- Performance improvements that do not change results.
- Bug fixes for crashes, import issues, or state corruption.
- Additional regression tests and documentation.

## Quality gates
Scan Lab v1.0 requires:
- Determinism checks (golden scans as regression tests).
- Artifact restore & replay audit.
- No known crashes or state corruption under normal use.

---
**Declaration:** Scan Lab is frozen as v1.0 under the above constraints. Future work should prioritize documentation, teaching materials, and new fidelity layers beyond 0‑D rather than feature growth within v1.0.
