"""Opt Lab entry contract — Certified Optimizer Phase 1.1–1.4.

Pure helpers (no NiceGUI imports) so the entry surface is lock-testable:
deck identity, three-step certified-search path, honesty phrases,
route targets into existing Systems Mode / Pareto Lab / Control Room
Certified Search surfaces, and a cheap last-run stamp summary (Phase 1.2).

Honesty phrases are sourced from ``certified_opt_honesty`` (Phase 1.3) to
avoid drift across decks.

L0 risk: none — navigation, copy, and stamp display only; certification
remains CCFS / frozen Evaluator. No user-facing label may carry internal
version tags (``vNNN``). Does not claim PROCESS retirement or an
authoritative optimum.
"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Tuple

from ui_nicegui.lib.certified_opt_honesty import (
    FORBIDDEN_POSITIVE_CLAIMS,
    PITCH_LINE,
    PROPOSED_CERTIFIED,
    REQUIRED_PHRASES,
)

# Deck display name — registered in DECK_LABELS / Helm nav.
OPT_LAB_DECK = "Opt Lab"

OPT_LAB_TITLE = "Opt Lab — Certified search"

OPT_LAB_TAGLINE = (
    "Search design space outside L0, then certify every claim with frozen truth — "
    "propose PointInputs, CCFS re-evaluates, and read VERIFIED vs REJECTED with atlas."
)

OPT_LAB_HONESTY_LINE = (
    f"Results are {PROPOSED_CERTIFIED} proposals that passed frozen re-eval — "
    "not an authoritative global optimum."
)

OPT_LAB_PITCH = PITCH_LINE

# Three-step path to a certified search entry (user-facing; no version tags).
OPT_LAB_STEPS: List[str] = [
    "Anchor a baseline in Point Designer (frozen evaluate) and pick the search path.",
    "Propose candidates — Systems Mode (targets/solve), Pareto Lab (blocking-OK front), "
    "or Control Room Certified Search (budgeted multi-knob).",
    "Read the certified front — VERIFIED vs REJECTED with NO-SOLUTION atlas; "
    "labels say Proposed — SHAMS-certified (not an authoritative optimum). "
    "Pareto Lab fronts are blocking-OK screening until CCFS re-certify.",
]

# Unified entry routes into existing surfaces (do not duplicate full decks).
# (button_label, target_deck, optional session_hook_id)
OPT_LAB_ROUTES: List[Tuple[str, str, str]] = [
    (
        "Systems Mode — target solve / alternatives",
        "Systems Mode",
        "systems_mode",
    ),
    (
        "Pareto Lab — blocking-OK front (intent-gate)",
        "Pareto Lab",
        "pareto_lab",
    ),
    (
        "Control Room — Certified Search",
        "Control Room",
        "certified_search",
    ),
]

OPT_LAB_STANCE_DOC = ("Certified Optimizer stance", "docs/CERTIFIED_OPTIMIZER.md")

# Phase 2.1 — propose-only continuous SearchDriver ids (core lives in
# ``src.optimization.slsqp_search_driver``; UI polish is secondary).
OPT_LAB_SLSQP_DRIVER_IDS: Tuple[str, ...] = ("slsqp", "slsqp_fallback")

OPT_LAB_SLSQP_HOOK_NOTE = (
    "Single-objective SLSQP/SQP-style search proposes PointInputs only "
    "(SciPy when available, pure-Python fallback otherwise); "
    "certify the reported best and a local neighborhood with CCFS — "
    "never treat driver scores as VERIFIED."
)

# Phase 3.1 — propose-only multi-objective SearchDriver ids.
OPT_LAB_NSGA2_DRIVER_IDS: Tuple[str, ...] = ("nsga2", "nsga2_fallback")

OPT_LAB_NSGA2_HOOK_NOTE = (
    "Multi-objective NSGA-II / MOEA search proposes PointInputs only "
    "(pure-Python NSGA-II fallback; optional pymoo when installed); "
    "blocking-OK-first shortlist must be CCFS-certified before any VERIFIED claim — "
    "never an authoritative optimum; "
    "dominated / REJECTED rows carry no_solution_atlas dominant hard mechanism."
)

# Phase 3.3 — shared Opt Lab ↔ Pareto certified-front viewer (no deck duplication).
OPT_LAB_CERTIFIED_FRONT_NOTE = (
    "Certified-front viewer unifies Opt Lab and Pareto Lab: CCFS shows VERIFIED/REJECTED + atlas; "
    "Pareto handoffs are blocking-OK screening only (not L0 FEASIBLE / not VERIFIED) — "
    "Proposed — SHAMS-certified applies after frozen re-certify, not an authoritative optimum."
)

# Phase 4.1 — surrogate propose-only SearchDriver (ranks only; CCFS certifies).
OPT_LAB_SURROGATE_DRIVER_IDS: Tuple[str, ...] = ("surrogate_propose",)

OPT_LAB_SURROGATE_HOOK_NOTE = (
    "Surrogate SearchDriver ranks and proposes PointInputs only "
    "(ridge acquisition via surrogate accel); every shortlist point re-evaluates "
    "with frozen L0 / CCFS — surrogate scores never set VERIFIED."
)

# Phrases that must appear in the entry contract (honesty lock).
OPT_LAB_REQUIRED_PHRASES: List[str] = list(REQUIRED_PHRASES) + [
    "propose",
    "CCFS",
]

# Forbidden in user-facing Opt Lab entry copy (positive claims).
OPT_LAB_FORBIDDEN_PHRASES: List[str] = list(FORBIDDEN_POSITIVE_CLAIMS) + [
    "optimizer-in-truth",
]


def opt_lab_user_facing_texts() -> List[str]:
    """All user-facing strings in the Opt Lab entry contract (for lock tests)."""
    texts: List[str] = [
        OPT_LAB_DECK,
        OPT_LAB_TITLE,
        OPT_LAB_TAGLINE,
        OPT_LAB_HONESTY_LINE,
        OPT_LAB_PITCH,
        OPT_LAB_STANCE_DOC[0],
        OPT_LAB_SLSQP_HOOK_NOTE,
        OPT_LAB_NSGA2_HOOK_NOTE,
        OPT_LAB_CERTIFIED_FRONT_NOTE,
        OPT_LAB_SURROGATE_HOOK_NOTE,
    ]
    texts.extend(OPT_LAB_STEPS)
    texts.extend(label for label, _, _ in OPT_LAB_ROUTES)
    return texts


def opt_lab_slsqp_driver_ids() -> Tuple[str, ...]:
    """Propose-only SLSQP SearchDriver ids exposed to Opt Lab (Phase 2.1)."""
    return OPT_LAB_SLSQP_DRIVER_IDS


def opt_lab_nsga2_driver_ids() -> Tuple[str, ...]:
    """Propose-only NSGA-II SearchDriver ids exposed to Opt Lab (Phase 3.1)."""
    return OPT_LAB_NSGA2_DRIVER_IDS


def opt_lab_surrogate_driver_ids() -> Tuple[str, ...]:
    """Propose-only surrogate SearchDriver ids exposed to Opt Lab (Phase 4.1)."""
    return OPT_LAB_SURROGATE_DRIVER_IDS


def apply_opt_lab_route_session(session: object, hook_id: str) -> None:
    """Prime session fields so the target deck opens on the certified-search surface."""
    if hook_id == "certified_search":
        session.cr_workflow_step = "6 · Chronicle"  # type: ignore[attr-defined]
        session.cr_section = "Chronicle"  # type: ignore[attr-defined]
        session.cr_chronicle_tab = "Certified Search"  # type: ignore[attr-defined]
    elif hook_id == "systems_mode":
        # Alternatives tab hosts budgeted feasible search + frontier panels.
        session.systems_workflow_step = "3 · Alternatives"  # type: ignore[attr-defined]
    elif hook_id == "pareto_lab":
        session.pareto_workflow_step = "1 · Setup & Run"  # type: ignore[attr-defined]


def store_opt_lab_last_run_stamp(session: object, stamp: Mapping[str, Any]) -> None:
    """Persist last ``opt_run_stamp.v1`` dict on the UI session (propose-only meta)."""
    session.opt_lab_last_run_stamp = dict(stamp)  # type: ignore[attr-defined]


def get_opt_lab_last_run_stamp(session: object) -> Optional[Mapping[str, Any]]:
    raw = getattr(session, "opt_lab_last_run_stamp", None)
    return dict(raw) if isinstance(raw, Mapping) else None


def opt_lab_last_run_stamp_summary(session: object) -> str:
    """Cheap one-line summary for the Opt Lab entry panel."""
    from src.optimization.opt_run_stamp import format_opt_run_stamp_summary

    return format_opt_run_stamp_summary(get_opt_lab_last_run_stamp(session))
