"""Plain-language Trade Study Studio labels — workflow tabs for fusion experts."""
from __future__ import annotations

from ui_nicegui.lib.display_labels import (
    DECK_FRONTIER_ATLAS,
    DECK_REGIME_MAPS,
    DECK_ROBUST_CERT,
    normalize_user_label,
)

TRADE_TABS = [
    "1 · Setup & Run",
    "2 · Explore Results",
    "3 · Interpret & Families",
    "4 · Export & Handoff",
    "5 · Advanced Tools",
]

ADVANCED_GROUPS = {
    "Frontier & certification": [
        DECK_FRONTIER_ATLAS,
        DECK_ROBUST_CERT,
    ],
    "Acceleration & optimizers": [
        "Feasible-First Surrogate Accelerator",
        "Optimizer Kits (External)",
        "Fast Optimistic Design (Two-Lane)",
    ],
    "Atlas & pathfinding": [
        "Design Family Atlas",
        DECK_REGIME_MAPS,
        "Mirage Pathfinding",
    ],
}

ALL_ADVANCED = [d for decks in ADVANCED_GROUPS.values() for d in decks]

_LEGACY_TAB_MAP = {
    "Study Setup & Run": "1 · Setup & Run",
}

TAB_HELP = {
    "1 · Setup & Run": (
        "Pick knob set, objectives, budget — LHS samples frozen truth; "
        "Pareto over blocking-OK (intent-gate) points only — not L0 FEASIBLE."
    ),
    "2 · Explore Results": "Interactive Pareto plot, blocking-OK / hard-fail shadow, design-family coloring.",
    "3 · Interpret & Families": "Blocking constraints, family mix, study narrative and self-audit.",
    "4 · Export & Handoff": "Study report + capsule JSON, restore replay, promote to Point Designer.",
    "5 · Advanced Tools": "Frontier atlas, robust certification, surrogate, optimizer kits, mirage pathfinding.",
}

DECK_SUBTITLE = (
    "Budgeted LHS trade studies over the **blocking-OK** set only "
    "(intent-gate — **not L0 FEASIBLE**) — truth frozen; optimizers propose only."
)

DEFAULT_TAB = "1 · Setup & Run"

DECISION_STATES = [
    "Run a new trade study",
    "Explore the blocking-OK Pareto set",
    "Understand families & blockers",
    "Export or promote a point",
    "Run atlas / certification / optimizers",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Setup & Run",
    DECISION_STATES[1]: "2 · Explore Results",
    DECISION_STATES[2]: "3 · Interpret & Families",
    DECISION_STATES[3]: "4 · Export & Handoff",
    DECISION_STATES[4]: "5 · Advanced Tools",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: (
        "Knob sets define the sampling hyper-rectangle. Objectives are **outputs** — "
        "Pareto never includes blocking-fail points (intent-gate — not L0 FEASIBLE)."
    ),
    DECISION_STATES[1]: "Color by **design_family** or **dominant_constraint** to see mechanism structure on the front.",
    DECISION_STATES[2]: "Family labels are narrative only — they do not change evaluator truth.",
    DECISION_STATES[3]: "Study capsule is the cross-deck handoff artifact (Pareto Lab, Compare, advanced decks).",
    DECISION_STATES[4]: "Surrogate and optimizer kits **propose**; SHAMS re-verifies every candidate.",
}


def normalize_trade_advanced_deck(name: str) -> str:
    s = normalize_user_label(str(name or "").strip())
    if s in ALL_ADVANCED:
        return s
    return ALL_ADVANCED[0] if ALL_ADVANCED else s


def normalize_trade_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in TRADE_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def teaching_banner(session) -> str | None:
    if not getattr(session, "trade_teaching_mode", False):
        return None
    state = str(getattr(session, "trade_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"
