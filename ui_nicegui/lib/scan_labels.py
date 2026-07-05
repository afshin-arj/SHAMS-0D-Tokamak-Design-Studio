"""Plain-language Scan Lab labels — workflow tabs for fusion experts."""

from __future__ import annotations

SCAN_TABS = [
    "1 · Setup & Run",
    "2 · Map & Probe",
    "3 · Interpret",
    "4 · Export & Archive",
]

_LEGACY_TAB_MAP = {
    "Cartography": "1 · Setup & Run",
    "Orientation": "4 · Export & Archive",
    "Cartography workbench": "2 · Map & Probe",
}

TAB_HELP = {
    "1 · Setup & Run": (
        "Choose the 2D slice (x/y axes, bounds, intent lenses) and run deterministic cartography."
    ),
    "2 · Map & Probe": (
        "Dominance / feasibility / robustness maps — probe a cell and inspect blocking margins."
    ),
    "3 · Interpret": (
        "Cliffs, coupling, local sensitivity, and next-tier 0-D insights (no optimization)."
    ),
    "4 · Export & Archive": (
        "Replayable artifacts, atlases, design families, restore, and freeze readiness."
    ),
}

DECK_SUBTITLE = (
    "Deterministic 2D cartography over the frozen evaluator — map limits, cliffs, "
    "and failure order. A microscope, not an engine."
)

DEFAULT_TAB = "1 · Setup & Run"

DECISION_STATES = [
    "Map my limits (2D slice)",
    "Probe a failing cell",
    "Explain cliffs & coupling",
    "Export atlas & archive",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Setup & Run",
    DECISION_STATES[1]: "2 · Map & Probe",
    DECISION_STATES[2]: "3 · Interpret",
    DECISION_STATES[3]: "4 · Export & Archive",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: (
        "Pick **two PointInputs axes** (e.g. Ip vs R₀). "
        "**Research** vs **Reactor** changes which constraints are blocking."
    ),
    DECISION_STATES[1]: (
        "Use **Dominant limiter map** first; gray means all cells are blocking-feasible in this slice. "
        "Probe indices (i, j) to read margins and failure order."
    ),
    DECISION_STATES[2]: (
        "**Robustness verdict** (KPI) ≠ per-cell robustness label ≠ local p-feasible map — "
        "each answers a different question. Counterfactual tools are visualization-only."
    ),
    DECISION_STATES[3]: (
        "Export **replay-format artifact** for restore. Enable **Include compact outputs** "
        "before the run if you need operating contours later."
    ),
}

# Workbench view keys (stored in session) → expert display labels
WB_VIEW_KEYS = [
    "Dominance (blocking)",
    "Feasibility (blocking)",
    "Robustness (proxy)",
    "Operating contours (outputs)",
]

WB_VIEW_LABELS = {
    "Dominance (blocking)": "Dominant limiter map",
    "Feasibility (blocking)": "Blocking feasibility",
    "Robustness (proxy)": "Local robustness (p-feasible proxy)",
    "Operating contours (outputs)": "Output contours",
}

QUICK_JUMP = {
    "D": ("2 · Map & Probe", "Dominance (blocking)"),
    "F": ("3 · Interpret", None),
    "I": ("2 · Map & Probe", None),  # toggles compare intents in workbench
    "C": ("3 · Interpret", "causality"),
}

INTENT_HELP = (
    "**Research** — TBR and some plant limits are diagnostic, not blocking. "
    "**Reactor** — full reactor-authority blocking set. Compare side-by-side when both are selected."
)

PROJECTION_CAVEAT = (
    "2D slice caveat: an off-axis constraint can dominate outside this plane. "
    "Treat maps as **slice truth**, not full-parameter truth."
)


def normalize_scan_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in SCAN_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def teaching_banner(session) -> str | None:
    if not getattr(session, "scan_teaching_mode", False):
        return None
    state = str(getattr(session, "scan_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"


def wb_view_options() -> list[str]:
    return list(WB_VIEW_KEYS)
