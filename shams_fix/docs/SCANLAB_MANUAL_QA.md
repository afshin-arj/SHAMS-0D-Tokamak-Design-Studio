# Scan Lab Manual QA Checklist (Freeze Sign-off)

Author: © 2026 Afshin Arjhangmehr  
Scope: SHAMS Tokamak 0-D Design Studio — Scan Lab  
Goal: Confirm Scan Lab is stable, deterministic, interpretation-safe, and export-ready.

Run this checklist after automated QA passes.

## A. Freeze contract and boundaries
- [ ] **Contract visible:** “Scan Lab Contract” expander exists and states *no optimization / no relaxation / no recommendation*.
- [ ] **Truth boundary honored:** Scan Lab does not modify Point Designer physics/constraints.
- [ ] **Intent lens clarity:** UI clearly says “same physics, different acceptance policy.”

## B. Core workflows (state + rerun safety)
Perform each step twice (to ensure rerun safety).

### 1) Setup → Run → Results
- [ ] Choose x/y variables, bounds, Nx/Ny.
- [ ] Run cartography scan.
- [ ] Results persist after any Streamlit rerun (changing a widget elsewhere).

### 2) Cell inspection
- [ ] Clicking/choosing a cell always shows consistent details (dominant constraint, margins, failure order).
- [ ] Causality trace panel (if enabled) renders without errors.

### 3) Intent split
- [ ] Run with both intents selected.
- [ ] Intent overlay/summary is consistent with policy (Research can be feasible when Reactor is not).

### 4) Robustness and topology
- [ ] Robustness labels appear (Robust/Balanced/Brittle/Knife-edge).
- [ ] Topology alerts (islands/holes) are shown when present and do not crash.

## C. Exports
From a completed scan:
- [ ] Download cartography report JSON works.
- [ ] Download points CSV works.
- [ ] Scan artifact JSON export works (schema v1).
- [ ] Claim Builder 1-page PDF export works.
- [ ] Signature Atlas export works and is exactly **10 pages**.

## D. Restore / replay
- [ ] Upload a previous scan artifact JSON → UI restores full scan state.
- [ ] Restored artifact uses upgrader without user intervention.
- [ ] Replay audit (run twice with same settings) passes and shows matching hashes.

## E. Error handling
- [ ] Invalid bounds show a human error message (no stack traces).
- [ ] If an optional module fails to import, the UI still loads and shows an “Import details” block.

## F. Preset naming logic
- [ ] Reference machine presets follow: `REF|<INTENT>|<FAMILY>`.
- [ ] Golden scans follow: `GOLDEN|...` naming logic and are consistent.

## Sign-off
- Date:
- SHAMS version:
- Tested on:
- Approved by:
