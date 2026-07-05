"""Plain-language Point Designer Truth Console workflow labels."""

from __future__ import annotations

PD_TRUTH_TABS = [
    "1 · Configure",
    "2 · Telemetry",
    "3 · Constraints",
]

_LEGACY_TAB_MAP = {
    "Configure": "1 · Configure",
    "Telemetry": "2 · Telemetry",
    "Constraints": "3 · Constraints",
}

TAB_HELP = {
    "1 · Configure": (
        "Machine geometry, plasma state, operating targets, authority overlays, and "
        "**Evaluate Point** — proposals only; frozen evaluator decides."
    ),
    "2 · Telemetry": (
        "Verdict-first KPIs, subsystem contracts, regime compass, constraint radar, "
        "physics deepening, and export bay after evaluation."
    ),
    "3 · Constraints": (
        "NO-SOLUTION mechanism atlas, constraint diff dossier, and hard/diagnostic "
        "margins — use when feasibility fails or you need attribution."
    ),
}

DECK_SUBTITLE = (
    "Frozen 0-D truth console — configure one operating point, evaluate through "
    "Evaluator.evaluate() → hot_ion_point(), read telemetry and constraints. "
    "No hidden optimization in L0."
)

DEFAULT_TAB = "1 · Configure"

DECISION_STATES = [
    "Set machine & authority overlays",
    "Evaluate frozen operating point",
    "Read performance & subsystem telemetry",
    "Diagnose constraint / NO-SOLUTION failures",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Configure",
    DECISION_STATES[1]: "1 · Configure",
    DECISION_STATES[2]: "2 · Telemetry",
    DECISION_STATES[3]: "3 · Constraints",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: (
        "Start with **Helm Console** intent (reactor vs research), then Configure "
        "geometry, plasma, and **Authority status board** overlays. Solver modes "
        "propose Ip/fG — SHAMS re-evaluates every candidate."
    ),
    DECISION_STATES[1]: (
        "Click **Evaluate Point** at the bottom of Configure. "
        "**direct** evaluates at your Ip/fG; **solver** nests for target H98/Q; "
        "**envelope** runs bounded vector solve."
    ),
    DECISION_STATES[2]: (
        "Open **Telemetry** for verdict KPIs, magnet card, fuel cycle, regime compass, "
        "and physics deepening. Hero strip above tabs mirrors the latest evaluation."
    ),
    DECISION_STATES[3]: (
        "Open **Constraints** for mechanism atlas and diff dossier. "
        "Hard failures block feasibility; diagnostic constraints are screening only."
    ),
}


def normalize_pd_tab(value: str) -> str:
    if value in PD_TRUTH_TABS:
        return value
    return _LEGACY_TAB_MAP.get(str(value), DEFAULT_TAB)


def teaching_banner(session) -> str:
    if not getattr(session, "pd_teaching_mode", True):
        return ""
    state = getattr(session, "pd_decision_state", DECISION_STATES[0])
    if state not in TEACHING_HINTS:
        return ""
    return TEACHING_HINTS[state]
