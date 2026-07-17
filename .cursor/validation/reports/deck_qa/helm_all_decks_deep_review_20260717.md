# Helm + decks deep review — 2026-07-17

UI-only NiceGUI hardening (no L0 / golden / evaluator changes).

## Already verified (not duplicated)

| Item | Status |
|------|--------|
| Systems Mode `render_posture_strip` uses `hero_kpi_cells` (PHYS-KPI-001) | OK |
| Systems Mode passes `design_intent` / `fuel_mode` | OK |
| `suggest_next_deck` → Systems Mode when PD point INFEASIBLE | OK |

## Findings → fixes this pass

### 1. Helm Captain's Ledger H98 honesty — **fixed**

**Finding:** `_render_posture` printed raw `H98` from outputs even when the point was INFEASIBLE, implying achieved confinement.

**Fix:** Route H98 through `hero_kpi_cells` (same policy as PD hero / Systems posture). Suppressed cells show `— (implied)` instead of a raw float.

### 2. Deck-switch latency / double remount — **audited, comment hardened**

**Finding:** `_switch_deck` already had same-deck early return, NAV-001 remount order (`_render_deck` then helm/status), and no settings-panel refresh. Handoffs that mutate same-deck state already use `force=True` (`navigate_to_point_designer`, `open_compare_deck`, Pareto/Scan/Forge export handoffs, etc.).

**Fix:** Clarified comments (single remount path; settings panel stays mounted). No behavior change beyond comment clarity.

### 3. Compare / Scan / Pareto empty states — **fixed**

| Deck | Before | After |
|------|--------|-------|
| Compare verdict | Empty + Load A & B only | Empty + Load A & B **and** Open Point Designer |
| Scan Lab verdict | Empty text only | Empty + Open Point Designer CTA |
| Pareto Lab verdict | Empty text only | Empty + Open Point Designer CTA |

Deck-level PD gates (`pd_prerequisite_gate` / Compare tip button) were already present.

### 4. Tests — **updated**

- `test_systems_posture_includes_h98_pfus` still asserts H98/Pfus; now also asserts `hero_kpi_cells`
- Added `test_suggest_next_deck_infeasible_points_to_systems`
- `test_helm_posture_shows_live_point` asserts `hero_kpi_cells` / H98 honesty path

## Pytest

```
cd SHAMS-0D
python -m pytest tests/test_nicegui_helm_console.py tests/test_nicegui_pd_hero_kpis.py -q --tb=line
```

Result: **65 passed** — see `_helm_decks_review_pytest.txt`.

## Remaining proposed items (not done)

1. **Handoff force hygiene:** several plain `switch_deck("X")` jumps (Suite → Control Room / PD, Pub → Systems / Suite) are fine for cross-deck nav; only add `force=True` if those paths start mutating session *on the already-active* deck before navigate.
2. **Scan/Pareto empty dual-CTA:** when a PD baseline already exists, prefer primary “Go to Setup & Run” and keep PD as secondary (currently always shows Open Point Designer on empty verdict).
3. ~~**Helm Ledger KPI strip**~~ — **fixed in follow-up:** Point line uses suppressed Q; H98 + Pfus captions when suppressed.
4. **Visual QA:** browser pass on INFEASIBLE point → Helm drawer + Systems Mode + PD hero all show consistent suppressed H98/Q.
5. **Compare without session eval:** keep allowing JSON-only A/B loads; ensure teaching mode still points Load A & B first.

## Physics coverage (readonly specialists — proposals only)

| Domain | UI coverage | Gap severity | Action |
|--------|-------------|--------------|--------|
| Confinement / H98 / IPB98 | Phase Envelopes + hero | Medium | Wire phase1 comparators into v396 display (overlay, no L0) |
| Exhaust / q_div | Telemetry proxy captions | Low (honesty OK) | Keep proxy labeling; Reactor intent for hard block |
| Magnets / HTS | Magnet card + nan→OFF | Low | OK for 0-D screening |
| Plant / Pe_net | Watermark + hero suppress | Low after this pass | OK |
| TBR / neutronics | Suites + deepening | Medium | Tritium closure study default overlay |
| Uncertainty | Uncertainty Contracts subdeck | Medium | Surface bands on hero when enabled |
| CD mix (NB/EC/LH) | Limited knobs | Medium | NBIC/ECCD authority overlay proposal |

**L0 proposals (deferred — require `/frozen-truth-change`):** extract v399 partition post-truth; density-peaking → τE in phase1.
