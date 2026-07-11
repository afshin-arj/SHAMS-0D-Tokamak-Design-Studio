"""Plain-language Control Room labels — workflow for fusion experts."""

from __future__ import annotations

CR_WORKFLOW_TABS = [
    "1 · Orient",
    "2 · Constitution",
    "3 · Provenance",
    "4 · Artifacts",
    "5 · Diagnostics",
    "6 · Chronicle",
]

_LEGACY_SECTION_MAP = {
    "Orientation": "1 · Orient",
    "Constitution": "2 · Constitution",
    "Provenance": "3 · Provenance",
    "Artifacts": "4 · Artifacts",
    "Diagnostics": "5 · Diagnostics",
    "Chronicle": "6 · Chronicle",
}

TAB_HELP = {
    "1 · Orient": "Launchpad, vocabulary, reference gallery, and model scope — review-room entry paths.",
    "2 · Constitution": "Frozen physics ledger, capability matrix, assumptions, and constraint governance.",
    "3 · Provenance": "Study protocol, repro lock, run audit overlays, case decks, scenario delta, regression.",
    "4 · Artifacts": "Explore run artifacts, run library, export bundles, benchmark reference table.",
    "5 · Diagnostics": "Gatechecks, interoperability, contract validator, session debug, forensics guide.",
    "6 · Chronicle": "Variable registry, sensitivity, feasibility maps, interval narrowing, study dashboard.",
}

DECK_SUBTITLE = (
    "Governance, provenance, exports, and expert diagnostics — organized for review rooms, not scroll walls."
)

DEFAULT_TAB = "1 · Orient"

DECISION_STATES = [
    "Find my workflow (launchpad)",
    "Read the physics constitution",
    "Audit study provenance & replay",
    "Explore or export run artifacts",
    "Debug wiring / run forensics",
    "Deep chronicle instruments",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Orient",
    DECISION_STATES[1]: "2 · Constitution",
    DECISION_STATES[2]: "3 · Provenance",
    DECISION_STATES[3]: "4 · Artifacts",
    DECISION_STATES[4]: "5 · Diagnostics",
    DECISION_STATES[5]: "6 · Chronicle",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: "Pick a launchpad path, then use **Open deck** to jump to Scan Lab, Forge, or Compare.",
    DECISION_STATES[1]: "Model Ledger and Capability Matrix are read-only frozen-truth documentation.",
    DECISION_STATES[2]: "Generate protocol + repro lock from a run artifact, then inspect authority overlays.",
    DECISION_STATES[3]: "Load session artifacts or browse `ui_runs/` — export bundles for reviewers.",
    DECISION_STATES[4]: "Run interoperability + contract validator before release; forensics uses current point inputs.",
    DECISION_STATES[5]: "Chronicle tools are downstream-only — they never modify the evaluator.",
}


def normalize_cr_tab(tab: str | None) -> str:
    if not tab:
        return DEFAULT_TAB
    t = str(tab).strip()
    if t in CR_WORKFLOW_TABS:
        return t
    return _LEGACY_SECTION_MAP.get(t, DEFAULT_TAB)


def teaching_banner(session) -> str:
    if not getattr(session, "cr_teaching_mode", True):
        return ""
    state = getattr(session, "cr_decision_state", "") or DECISION_STATES[0]
    return TEACHING_HINTS.get(state, "")
