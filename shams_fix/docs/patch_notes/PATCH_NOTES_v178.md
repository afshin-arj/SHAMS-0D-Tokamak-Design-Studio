# SHAMS / Tokamak 0-D Design Studio — Patch Notes (v178 series)

## v178.10 (2026-01-22)
- **Fix:** Systems solver crash `base_eval` referenced before assignment (was caused by a bad early-return indentation + `trace` init order).
- **Fix/UI:** **Seeded Feasibility Recovery** panel is now always visible (not only when precheck is infeasible).
- **Fix/UI:** `Precheck report (detailed)` can no longer appear blank: it always shows a minimal summary plus a **raw report (debug)** fallback.
- **UI cleanup:** Removed legacy feature-version tags from user-facing headings (e.g. `Stateful Results (v92)` → `Stateful Results`, `Panel Availability Map (v175)` → `Panel Availability Map`).

## v178.9
- Design Intent metadata is propagated in Point Designer logs/artifacts (design_intent + constraint_policy fields).

## v178.8
- Fix: UI indentation error in exports panel.

## v178.7
- Design Intent selector surfaced consistently across modes.

## v178.6
- Intent-aware precheck messaging (Research intent no longer claims “reactor hard set”).

## v178.5
- Point Designer: constraint policy split (blocking vs diagnostic vs ignored) displayed/logged.

## v178.4
- Design Intent introduced (Research vs Reactor) with intent-aware constraint policy and artifacts.
