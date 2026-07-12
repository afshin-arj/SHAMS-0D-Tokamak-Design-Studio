"""Expert study workflow — phase map, deck actions, and next-step guidance."""
from __future__ import annotations

from typing import Any, Optional

from ui_nicegui.decks.labels import DECK_LABELS
from ui_nicegui.lib.deck_workflow import DECK_WORKFLOW_CAPTIONS, DECK_WORKFLOW_STEP
from ui_nicegui.lib.helm_labels import HELM_NAV_GROUPS

# Phase index 1–5 matching HELM_NAV_GROUPS order.
WORKFLOW_PHASES: list[tuple[str, str]] = [
    ("Anchor", "Define one operating point; get a feasibility verdict."),
    ("Map & close", "Cartography, then integrated plant/systems closure."),
    ("Compare & trade", "Diff artifacts, Pareto fronts, certified trade studies."),
    ("Concepts", "Compile intent; explore machine families and archives."),
    ("Evidence & audit", "Benchmarks, batch campaigns, provenance, export."),
]

DECK_TO_PHASE: dict[str, int] = {}
for phase_idx, (_, _, decks) in enumerate(HELM_NAV_GROUPS, start=1):
    for deck in decks:
        DECK_TO_PHASE[deck] = phase_idx

# What to do *now* on each deck (fusion-expert verbs, 2–3 lines max).
DECK_NOW_ACTIONS: dict[str, list[str]] = {
    "Point Designer": [
        "Configure geometry, plasma, and plant inputs.",
        "Evaluate — read verdict, dominant constraint, and margins.",
        "Use Constraints atlas before advancing.",
    ],
    "Scan Lab": [
        "Pick two scan axes and run a feasibility cartography.",
        "Inspect first-failure topology on the map.",
        "Export Scan Atlas capsule for replay.",
    ],
    "Systems Mode": [
        "Close plant power balance and systems constraints.",
        "Review feasibility map and recovery posture.",
        "Save run artifact for Compare or Pareto.",
    ],
    "Compare": [
        "Load baseline and scenario artifacts (A & B).",
        "Review performance, constraint, and structural diffs.",
        "Export comparison bundle for reviewers.",
    ],
    "Pareto Lab": [
        "Define objectives on the feasible set only.",
        "Separate optimistic vs robust lanes; filter mirages.",
        "Export publication pack from the frontier.",
    ],
    "Trade Study Studio": [
        "Set up certified trade study parameters.",
        "Run frontier atlas and robust certification.",
        "Hand off to external optimizer kits if needed.",
    ],
    "Reactor Design Forge": [
        "Compile design intent and machine-finder criteria.",
        "Run staged exploration; archive candidates to casebook.",
        "Open machine dossier for review-room narrative.",
    ],
    "Publication Benchmarks": [
        "Evaluate a reference preset on the Constitutional Atlas (Tab 1).",
        "Generate publication CSV/ZIP pack and inspect blocking pass/fail (Tab 2).",
        "Compare cross-code semantics or open System Suite for numeric PROCESS parity (Tab 3).",
        "Export reviewer/licensing packs or session evidence (Tabs 4–5).",
    ],
    "System Suite": [
        "Review plant closure and net-electric ledger (Tab 1).",
        "Check ops/thermal traces and lifetime/TBR budgets (Tabs 2–3).",
        "Run envelope tools or export campaign/parity packs (Tabs 4–5).",
    ],
    "Control Room": [
        "Generate study protocol and repro lock from artifact.",
        "Inspect run audit overlays and scenario delta.",
        "Export evidence bundle for audit trail.",
    ],
}

DECK_SHORT_VERBS: dict[str, str] = {
    "Point Designer": "Evaluate point",
    "Scan Lab": "Map design space",
    "Systems Mode": "Close systems",
    "Compare": "Diff A vs B",
    "Pareto Lab": "Build frontier",
    "Trade Study Studio": "Certify trade study",
    "Reactor Design Forge": "Explore concepts",
    "Publication Benchmarks": "Benchmark constitution",
    "System Suite": "Review system overlays",
    "Control Room": "Seal & export",
}


def deck_phase(deck: str) -> int:
    return DECK_TO_PHASE.get(deck, 1)


def phase_title(phase: int) -> str:
    if 1 <= phase <= len(WORKFLOW_PHASES):
        return WORKFLOW_PHASES[phase - 1][0]
    return "Study"


def has_point_evaluation(session: Any) -> bool:
    return isinstance(getattr(session, "pd_last_outputs", None), dict)


def has_compare_slots(session: Any) -> bool:
    a = getattr(session, "cmp_slot_a", None)
    b = getattr(session, "cmp_slot_b", None)
    return isinstance(a, dict) or isinstance(b, dict)


def suggest_next_deck(session: Any, active_deck: str) -> tuple[Optional[str], str]:
    """Return (recommended deck or None, plain-language reason)."""
    if not has_point_evaluation(session):
        if active_deck != "Point Designer":
            return ("Point Designer", "No evaluation yet — anchor a point under frozen truth first.")
        return (None, "Evaluate the current point before moving to cartography.")

    try:
        idx = DECK_LABELS.index(active_deck)
    except ValueError:
        return (None, "")

    if active_deck == "Point Designer":
        return ("Scan Lab", "Point evaluated — map feasible regions before committing.")

    if active_deck == "Scan Lab" and not (
        isinstance(getattr(session, "scan_cartography_report", None), dict)
        or isinstance(getattr(session, "scan_cartography_artifact", None), dict)
    ):
        return (None, "Run a cartography scan or continue to Systems Mode when ready.")

    if active_deck == "Systems Mode":
        return ("Compare", "Systems closed — diff baseline vs scenario artifacts.")

    if active_deck == "Compare" and not has_compare_slots(session):
        return (None, "Load both comparison artifacts, then review constraint diffs.")

    if idx < len(DECK_LABELS) - 1:
        nxt = DECK_LABELS[idx + 1]
        verb = DECK_SHORT_VERBS.get(nxt, nxt)
        return (nxt, f"Next in workflow: {verb}.")

    return (None, "Workflow complete — seal study in Control Room exports.")


def workflow_progress(session: Any) -> dict[str, bool]:
    """Milestone flags for phase strip styling."""
    evaluated = has_point_evaluation(session)
    scanned = isinstance(getattr(session, "scan_cartography_report", None), dict) or isinstance(
        getattr(session, "scan_cartography_artifact", None), dict
    )
    compared = has_compare_slots(session)
    sealed = isinstance(getattr(session, "cr_study_protocol_last", None), dict)
    return {
        "evaluated": evaluated,
        "scanned": scanned,
        "compared": compared,
        "sealed": sealed,
    }


def phase_completion(phase: int, progress: dict[str, bool]) -> bool:
    if phase == 1:
        return progress.get("evaluated", False)
    if phase == 2:
        return progress.get("scanned", False)
    if phase == 3:
        return progress.get("compared", False)
    if phase == 5:
        return progress.get("sealed", False)
    return False
