# PROCESS ↔ SHAMS Crosswalk

This crosswalk is for migration and reviewer comfort. It is not an attempt to emulate PROCESS behavior.

**Canonical community guide (Phase 3.1):** [`PROCESS_TO_SHAMS_MIGRATION_GUIDE.md`](PROCESS_TO_SHAMS_MIGRATION_GUIDE.md) — IN.DAT→Case/`PointInputs`, MFILE→artifacts, constraint policy, CCFS propose-only, citation + METHOD-ONLY honesty.

## Core difference
- PROCESS searches for machines using implicit objective/penalty structure.
- SHAMS determines what machines can exist (constraints-first) and records why.

## Mapping (high level)
- PROCESS IN.DAT → SHAMS **Case** / **PointInputs** (intent + lens + bounds + budgets)
- PROCESS output tables → SHAMS **Artifacts** (truth + closure + margins + conflicts)
- PROCESS optimization knobs → SHAMS **Explore controls** (non-prescriptive, feasibility-first)
- PROCESS “best design” → **Not a SHAMS concept**

## What SHAMS adds
- Constraint conflict map
- Margin spend narrative
- First-kill-under-uncertainty diagnosis
- Deterministic replay capsules
- NO-SOLUTION atlas on infeasible artifacts (`no_solution_atlas.v1`)
- CCFS firewall (external proposers re-certified; claims ≠ VERIFIED when hard fail)

## Related
- Domain checklist: `PROCESS_TO_SHAMS_MAPPING.md`
- Limitations / anti-overclaim: `LIMITATIONS.md`
- Campaign roadmap: `PROCESS_SURPASS_ROADMAP.md`
