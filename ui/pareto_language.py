"""Pareto UI frozen language.
Centralizing these strings prevents semantic drift after freeze.
"""

PARETO_LOCK_LINE = (
    "🔒 **Pareto Lab is frozen** — Trade-off cartography over **blocking-OK** "
    "(intent-gate) designs only — **not L0 FEASIBLE**. "
    "No optimization, relaxation, or recommendations."
)

PARETO_OPTIMAL_DEF = (
    "ℹ️ **Definition (SHAMS):** This lab reports *non-dominated blocking-OK* points "
    "for the declared objectives and intent-gate. "
    "This is a **trade-off slice**: it is descriptive, blocking-OK-only "
    "(**not** Point Designer L0 FEASIBLE), and never a recommendation."
)

TRUST_BOUNDARIES = [
    "✔ blocking-OK only (intent-aware screening — not L0 FEASIBLE)",
    "✔ Deterministic and replayable",
    "✔ Policy-explicit",
    "✖ Not exhaustive over continuous space",
    "✖ Not predictive outside sampled bounds",
]

FREEZE_STAMP = "Pareto — Frozen (semantic v1)"
