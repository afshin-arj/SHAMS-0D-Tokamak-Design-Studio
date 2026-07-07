"""Plain-language Reactor Design Forge labels — workflow tabs."""
from __future__ import annotations

FORGE_TABS = [
    "1 · Compile Intent",
    "2 · Setup & Search",
    "3 · Workbench",
    "4 · Instruments",
    "5 · Capsules & Export",
]

_LEGACY_TAB_MAP = {
    "Intent Compiler": "1 · Compile Intent",
    "Machine Finder": "2 · Setup & Search",
    "Capsules": "5 · Capsules & Export",
    "4 · Capsules & Export": "5 · Capsules & Export",
}

TAB_HELP = {
    "1 · Compile Intent": "Algebraic intent → candidate PointInputs. Audit with frozen evaluator before applying.",
    "2 · Setup & Search": "Intent, lens, bounds, advanced engine options, hybrid Machine Finder run (or staged phases).",
    "3 · Workbench": "Archive scatter/table, candidate inspector, conflict atlas, review bench.",
    "4 · Instruments": "Full expert cockpit — all legacy Forge views grouped by task (60+ instruments).",
    "5 · Capsules & Export": (
        "Restore/diff/export run capsules, cross-deck handoffs (Compare, Scan Lab, Systems Mode), "
        "and design-card markdown download."
    ),
}

DECK_SUBTITLE = (
    "Non-authoritative candidate workspace — archives + traces feed the frozen evaluator; nothing auto-applies."
)

DEFAULT_TAB = "1 · Compile Intent"

DECISION_STATES = [
    "Compile intent to a candidate",
    "Run a machine search",
    "Inspect archive & resistance",
    "Deep-dive instruments",
    "Export or restore a capsule",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Compile Intent",
    DECISION_STATES[1]: "2 · Setup & Search",
    DECISION_STATES[2]: "3 · Workbench",
    DECISION_STATES[3]: "4 · Instruments",
    DECISION_STATES[4]: "5 · Capsules & Export",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: "Compilation is algebraic only — always **Audit** before applying to Point Designer.",
    DECISION_STATES[1]: "Start with 3–5 variables and Medium bounds; use **Staged run** to execute phases one-by-one.",
    DECISION_STATES[2]: "Archive scores are **non-authoritative** — feasibility is from frozen truth.",
    DECISION_STATES[3]: "Pick a **category** then instrument — Review Trinity, dossier, DOI export, etc.",
    DECISION_STATES[4]: (
        "Capsules replay metadata; use **handoffs** here to send archive rows to Compare or Scan Lab; "
        "re-audit any promoted candidate in Point Designer."
    ),
}

WORKBENCH_VIEWS = [
    "Archive overview",
    "Candidate inspector",
    "Machine dossier (compact)",
    "Resistance & conflicts",
    "Review bench",
    "Run dashboard",
    "Ladder histogram",
]


def normalize_forge_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in FORGE_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def teaching_banner(session) -> str | None:
    if not getattr(session, "forge_teaching_mode", False):
        return None
    state = str(getattr(session, "forge_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"
