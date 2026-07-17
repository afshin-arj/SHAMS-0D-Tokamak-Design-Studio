"""Studio default entry — verdict-first onboarding contract (Independence Phase 3.4).

Pure helpers (no NiceGUI imports) so the default-entry contract is lock-testable:
what SHAMS answers, NO-SOLUTION as a first-class outcome, champion templates as
one-click starting points, and onboarding doc links (migration guide, champion cases).

L0 risk: none — this module only proposes PointInputs into the UI session;
Point Designer evaluates via the frozen Evaluator as always. No user-facing
label may carry internal overlay version tags. Does not claim PROCESS retirement.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from studies.champion_cases import (  # type: ignore
        load_champion_definitions,
        resolve_inputs,
    )
except ImportError:  # pragma: no cover
    from src.studies.champion_cases import (
        load_champion_definitions,
        resolve_inputs,
    )

try:
    from models.reference_machines import REFERENCE_MACHINES  # type: ignore
except ImportError:  # pragma: no cover
    from src.models.reference_machines import REFERENCE_MACHINES

try:
    from schema.inputs import PointInputs  # type: ignore
except ImportError:  # pragma: no cover
    from src.schema.inputs import PointInputs

from ui_nicegui.lib.pd_intent_policy import design_intent_key


STUDIO_ENTRY_TITLE = "Start a systems study"

STUDIO_ENTRY_TAGLINE = (
    "Evaluate one operating point under frozen truth and read the certified verdict — "
    "feasible with margins, or NO-SOLUTION with the mechanism that blocks it."
)

# What SHAMS answers — the feasibility-authority pitch, verbatim for the entry card.
STUDIO_WHAT_SHAMS_ANSWERS: List[str] = [
    "Is this design admissible under the declared hard constraints?",
    "Why did it fail — which mechanism and constraint dominate?",
    "What breaks first under uncertainty?",
    "Can I cite and reproduce this verdict without trusting an optimization path?",
]

STUDIO_NO_SOLUTION_NOTE = (
    "NO-SOLUTION is a first-class result, not an error: SHAMS reports which designs "
    "cannot exist and attributes the blocking mechanism instead of negotiating "
    "constraints until a solver converges."
)

STUDIO_STEPS = [
    "Pick a starting point — champion template, reference machine, or your own inputs.",
    "Click Evaluate Point — the frozen evaluator runs once, deterministically.",
    "Read the verdict — feasible margins, or the NO-SOLUTION mechanism atlas.",
]

# Onboarding docs (labels are user-facing — keep them free of version tags).
STUDIO_DOC_LINKS: List[Tuple[str, str]] = [
    ("PROCESS → SHAMS migration guide", "docs/PROCESS_TO_SHAMS_MIGRATION_GUIDE.md"),
    ("Champion feasibility cases", "docs/CHAMPION_CASES.md"),
    ("Scoped PROCESS retirement evidence", "docs/PROCESS_RETIREMENT_REPORT.md"),
    ("Cite-SHAMS handoff pack", "docs/CITE_SHAMS_HANDOFF.md"),
]

# Map champion Design Intent onto the Helm Console mission-profile options.
_INTENT_KEY_TO_SESSION_INTENT = {
    "research": "Experimental Device (research)",
    "reactor": "Power Reactor (net-electric)",
}


def session_design_intent_for(design_intent: str) -> str:
    """Map a champion-case design intent onto a Helm mission-profile label."""
    return _INTENT_KEY_TO_SESSION_INTENT[design_intent_key(design_intent)]


def champion_template_options() -> List[Dict[str, Any]]:
    """Deterministic champion template menu for the Studio entry panel.

    Labels come from the case titles (scientific names only — no version tags).
    Infeasible templates are included on purpose: NO-SOLUTION stories are part
    of the default entry experience.
    """
    options: List[Dict[str, Any]] = []
    for case in load_champion_definitions():
        options.append(
            {
                "case_id": str(case["case_id"]),
                "label": str(case.get("title") or case["case_id"]),
                "family": str(case.get("family") or ""),
                "story": str(case.get("story") or ""),
                "design_intent": str(case.get("design_intent") or "Research"),
                "expect_hard_feasible": case.get("expect_hard_feasible"),
            }
        )
    return options


def _case_by_id(case_id: str) -> Dict[str, Any]:
    for case in load_champion_definitions():
        if str(case["case_id"]) == str(case_id):
            return case
    raise KeyError(f"Unknown champion case: {case_id!r}")


def champion_template_overrides(case_id: str) -> Dict[str, Any]:
    """Normalized explicit overrides a champion template declares.

    Only the keys declared by the template (reference-machine preset + case
    overrides) are returned, with values normalized through PointInputs.
    Session defaults fill the remaining knobs, exactly as when a user types
    the same values into Configure by hand.
    """
    case = _case_by_id(case_id)
    explicit: set[str] = set()
    ref_name = str(case.get("reference_machine") or "").strip()
    if ref_name:
        explicit.update(REFERENCE_MACHINES[ref_name].keys())
    for key in (case.get("inputs") or {}):
        if not str(key).startswith("_"):
            explicit.add(str(key))
    resolved = resolve_inputs(case)
    return {k: resolved[k] for k in sorted(explicit) if k in resolved}


def apply_champion_template(session: Any, case_id: str) -> Dict[str, Any]:
    """Load a champion template into the Point Designer session (propose-only).

    Clears any cached evaluation, pushes the full champion PointInputs basis
    through the canonical Helm reference-machine path (which also syncs
    ``Paux_for_Q_MW`` to the template's heating power and the solver bounds),
    and aligns the mission profile with the case Design Intent. Returns the
    template's explicit overrides. The user still clicks Evaluate Point —
    nothing is auto-evaluated.
    """
    from ui_nicegui.lib.helm_helpers import on_design_intent_changed, push_point_inputs_to_session
    from ui_nicegui.lib.session_store import clear_point_designer

    case = _case_by_id(case_id)
    overrides = champion_template_overrides(case_id)
    clear_point_designer(session)
    push_point_inputs_to_session(session, PointInputs.from_dict(resolve_inputs(case)))
    prev_intent = str(session.design_intent)
    new_intent = session_design_intent_for(str(case.get("design_intent") or "Research"))
    if prev_intent != new_intent:
        # Canonical Helm intent handler: cache invalidation + governance preset.
        on_design_intent_changed(session, prev_intent, new_intent)
    return overrides
