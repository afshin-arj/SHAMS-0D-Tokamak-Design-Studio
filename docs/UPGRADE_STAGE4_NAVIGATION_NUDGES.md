# Stage 4 — Design-space navigation

Adds `frontier.nudges.directional_nudges()` and `tools/nudge_point.py`.

Given an infeasible point, it ranks knob deltas that are predicted (locally) to fix the worst hard constraint with minimal objective penalty.
