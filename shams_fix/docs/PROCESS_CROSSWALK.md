# PROCESS ↔ SHAMS Crosswalk

This crosswalk is for migration and reviewer comfort. It is not an attempt to emulate PROCESS behavior.

## Core difference
- PROCESS searches for machines using implicit objective/penalty structure.
- SHAMS determines what machines can exist (constraints-first) and records why.

## Mapping (high level)
- PROCESS IN.DAT → SHAMS **Case** (intent + lens + bounds + budgets)
- PROCESS output tables → SHAMS **Artifacts** (truth + closure + margins + conflicts)
- PROCESS optimization knobs → SHAMS **Explore controls** (non-prescriptive, feasibility-first)
- PROCESS “best design” → **Not a SHAMS concept**

## What SHAMS adds
- Constraint conflict map
- Margin spend narrative
- First-kill-under-uncertainty diagnosis
- Deterministic replay capsules

