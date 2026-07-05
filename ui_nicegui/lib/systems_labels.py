"""Plain-language Systems Mode labels — workflow-ordered tabs for fusion experts."""

from __future__ import annotations

# Five workflow tabs (Posture is always pinned above tabs, not a tab)
SYSTEMS_TABS = [
    "1 · Targets",
    "2 · Check & Solve",
    "3 · Alternatives",
    "4 · Apply",
    "5 · Review",
]

_LEGACY_TAB_MAP = {
    "Posture": "5 · Review",
    "Solve": "2 · Check & Solve",
    "Recover": "3 · Alternatives",
    "Explore": "3 · Alternatives",
    "Apply": "4 · Apply",
    "Audit": "5 · Review",
    "Setup": "1 · Targets",
    "Diagnose": "2 · Check & Solve",
    "Compare/Apply": "4 · Apply",
    "Export": "5 · Review",
    "Advanced": "5 · Review",
}

TAB_HELP = {
    "1 · Targets": "What the point must achieve (Q, H98, P_net) and which variables the solver may adjust (I_p, f_G, P_aux).",
    "2 · Check & Solve": "Step ① bound feasibility check, then Step ② Newton target solve.",
    "3 · Alternatives": "If precheck or solve fails — nearest feasible recovery or budgeted search.",
    "4 · Apply": "Promote one candidate to Point Designer and re-evaluate through frozen truth.",
    "5 · Review": "Constraint ledger, rankings, exports, certifications, and run history.",
}

DECK_SUBTITLE = (
    "Target-solve cockpit around frozen Point Designer physics — "
    "samples, solves, and ranks candidates; never modifies evaluator truth."
)

DEFAULT_TAB = "2 · Check & Solve"

DECISION_STATES = [
    "Diagnose infeasibility",
    "Recover feasibility near seed",
    "Choose a compromise (best-compromise)",
    "Explore trade space (scan/frontier)",
    "Apply & iterate (update Base/x0)",
]

TEACHING_HINTS = {
    "Diagnose infeasibility": "Run **Step ① precheck** — read the dominant limiter before changing targets.",
    "Recover feasibility near seed": "Open **3 · Alternatives** → seeded recovery. Increase eval budget if the seed stays infeasible.",
    "Choose a compromise (best-compromise)": "Use feasible search, rank candidates, then promote the best compromise on **4 · Apply**.",
    "Explore trade space (scan/frontier)": "Inspect atlas / frontier on expert view, then export audit artifacts on **5 · Review**.",
    "Apply & iterate (update Base/x0)": "Apply a candidate to Point Designer, re-evaluate through frozen truth, and re-run precheck.",
}


def teaching_banner(session) -> str | None:
    if not getattr(session, "systems_teaching_mode", False):
        return None
    state = str(getattr(session, "systems_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"


def normalize_systems_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in SYSTEMS_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def next_action_hint(
    *,
    has_artifact: bool,
    artifact_source: str | None,
    targets_ok: bool,
    precheck_ok: bool | None,
    solve_ok: bool | None,
    n_candidates: int,
) -> str:
    if not has_artifact:
        return "Evaluate in **Point Designer** first to establish a machine baseline."
    if not targets_ok:
        return "Open **1 · Targets** — enable at least one target and one adjustable variable."
    if precheck_ok is False:
        return "Precheck failed — apply suggested fixes on **2 · Check & Solve**, or try **3 · Alternatives**."
    if precheck_ok is None:
        return "Run **Step ① precheck** on **2 · Check & Solve** before target solve."
    if artifact_source == "point_designer_fallback" or solve_ok is None:
        return "Run **Step ② target solve** on **2 · Check & Solve**."
    if solve_ok is False:
        return "Target solve did not converge — adjust targets or try **3 · Alternatives**."
    if n_candidates > 0:
        return f"{n_candidates} candidate(s) ready — promote on **4 · Apply**."
    if precheck_ok and solve_ok:
        return "Feasible solve complete — explore **3 · Alternatives** or export on **5 · Review**."
    return "Review design status above, then continue the workflow left to right."
