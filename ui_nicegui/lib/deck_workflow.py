"""Expert implementation workflow — deck order, captions, and navigation hints."""
from __future__ import annotations

from ui_nicegui.decks.labels import DECK_LABELS

# Fusion-expert implementation sequence: anchor → map → compare → concept → evidence.
DECK_WORKFLOW_CAPTIONS: dict[str, str] = {
    "Point Designer": "Anchor one operating point — geometry, plasma, plant inputs, feasibility verdict.",
    "Scan Lab": "Map feasible regions in parameter space (cartography before commitment).",
    "Systems Mode": "Monte Carlo precheck and Newton target solve — proposes inputs; never changes L0 truth.",
    "Opt Lab": "Certified-search entry — three-step propose→CCFS path into Systems Mode / Pareto / Certified Search.",
    "Compare": "Diff baseline vs scenario artifacts — performance, constraints, structure.",
    "Pareto Lab": "Extract nondominated feasible frontiers under explicit objectives.",
    "Trade Study Studio": "Run certified trade studies, robust lanes, and surrogate exploration.",
    "Reactor Design Forge": "Compile design intent and explore reactor concept families.",
    "Publication Benchmarks": "Constitutional atlas, reviewer packs, cross-code parity.",
    "System Suite": "Read-only L1 engineering overlays on your Point Designer artifact (not Systems Mode solver).",
    "Control Room": "Governance, provenance, exports, and review-room diagnostics.",
}

DECK_WORKFLOW_STEP: dict[str, int] = {name: i + 1 for i, name in enumerate(DECK_LABELS)}


def deck_workflow_caption(deck: str) -> str:
    step = DECK_WORKFLOW_STEP.get(deck)
    cap = DECK_WORKFLOW_CAPTIONS.get(deck, "")
    if step and cap:
        return f"Workflow step {step} · {cap}"
    return cap


# Disambiguate near-homonyms in the Helm deck list (Systems Mode ≠ System Suite).
_DECK_NAV_ALIASES: dict[str, str] = {
    "Systems Mode": "Systems Mode — Close",
    "Opt Lab": "Opt Lab — Certified search",
    "System Suite": "System Suite — L1 overlays",
}


def deck_nav_short_label(deck: str) -> str:
    """Sidebar button label with workflow step prefix."""
    step = DECK_WORKFLOW_STEP.get(deck)
    label = _DECK_NAV_ALIASES.get(deck, deck)
    if step is None:
        return label
    return f"{step}. {label}"
