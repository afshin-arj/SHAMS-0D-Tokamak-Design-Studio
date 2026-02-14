"""Pareto UI frozen language.
Centralizing these strings prevents semantic drift after freeze.
"""

PARETO_LOCK_LINE = "🔒 **Pareto Lab is frozen** — Trade-off cartography over **feasible** designs only. No optimization, relaxation, or recommendations."

PARETO_OPTIMAL_DEF = (
    "ℹ️ **Definition (SHAMS):** This lab reports *non-dominated feasible* points for the declared objectives and intent. "
    "This is a **trade-off slice**: it is descriptive, feasible-only, and never a recommendation."
)

TRUST_BOUNDARIES = [
    "✔ Feasible-only (intent-aware)",
    "✔ Deterministic and replayable",
    "✔ Policy-explicit",
    "✖ Not exhaustive over continuous space",
    "✖ Not predictive outside sampled bounds",
]

FREEZE_STAMP = "Pareto — Frozen (semantic v1)"
