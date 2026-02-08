"""UI language & posture freeze.

This centralizes the few terms that must remain stable before external exposure.

We do not attempt to police all text, but we provide canonical phrases for:
- Non-prescriptive posture
- Trade-off (Pareto) semantics
- Existence / failure / margin framing
"""

FREEZE_VERSION = "v208"

CANON = {
    "non_prescriptive_banner": "Non-prescriptive workspace: SHAMS never ranks, recommends, or selects machines.",
    "no_best_design": "No 'best design' exists here — only feasible machines, conflicts, and budgets.",
    "tradeoff_slice": "Trade-off slice (feasible-only). No winners.",
    "existence_proof": "Existence proof",
    "stress_story": "Stress story",
    "positioning": "Positioning",
    "margin_first": "Margins first: what this machine spends to exist.",
    "external_exposure_gate": "External exposure is permitted only after language/posture freeze and review-room readiness are satisfied.",
}


FORBIDDEN_PHRASES = [
    "best design",
    "optimal",
    "we recommend",
    "recommended",
]
