# SHAMS–FUSION-X v79 Release Notes (Publishable)
**Author:** Afshin Arjhangmehr  
**Release date:** 2026-01-08

## Overview
v79 adds a UI-visible **Performance Panel** and threads performance options (cache + solver backend) through Systems Mode explicitly.

## UI Additions
- Sidebar *Performance* expander:
  - evaluation cache enable/size controls
  - solver backend selection (Systems Mode): `hybrid_newton` (default) or `broyden` (opt-in)
  - Performance Panel toggle

## Solver Telemetry (auditable)
- Systems Mode records wall-clock solve time.
- Trace includes a final `cache_stats` event with evaluator cache hit/miss/eviction stats and backend selection.

## Guarantees
- Physics unchanged.
- Default behavior unchanged.
- All options are explicit and logged.
