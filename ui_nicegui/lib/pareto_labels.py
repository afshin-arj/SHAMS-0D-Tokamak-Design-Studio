"""Plain-language Pareto Lab labels — workflow tabs for fusion experts."""

from __future__ import annotations

PARETO_TABS = [
    "1 · Setup & Run",
    "2 · Explore Frontier",
    "3 · Interpret & Audit",
    "4 · Export & Handoff",
    "5 · External Tools",
]

EXTERNAL_GROUPS = {
    "Robust screening": [
        "Robust Pareto Frontier (Phase+UQ)",
        "Certified Optimization Orchestrator",
    ],
    "Atlas & narratives": [
        "Regime-Conditioned Pareto Atlas 2.0",
        "Design Family Narratives",
    ],
    "Optimizers & evidence": [
        "Feasible Optimizer (External)",
        "Concept Optimization Cockpit",
        "External Optimization Workbench",
        "External Optimizer Suite",
        "External Optimizer Co-Pilot",
        "External Optimization Interpretation",
        "Optimization Evidence Packs",
    ],
}

ALL_EXTERNAL = [t for tools in EXTERNAL_GROUPS.values() for t in tools]

_LEGACY_TAB_MAP = {
    "Internal Pareto Frontier": "1 · Setup & Run",
}

TAB_HELP = {
    "1 · Setup & Run": "Declare bounds, objectives, intent, and sample the blocking-OK set (LHS; intent-gate). Results persist after run.",
    "2 · Explore Frontier": "Interactive Pareto plot — pick axes, inspect blocking-OK set, hard-fail shadow, robust overlay.",
    "3 · Interpret & Audit": "Trade-off matrix, knee regions, redundancy hints, self-audit checklist.",
    "4 · Export & Handoff": "Replay artifact, publication ZIP, promote to Point Designer, Scan Lab / Systems Mode handoffs.",
    "5 · External Tools": "Firewalled optimizers and robust screening — truth remains frozen.",
}

DECK_SUBTITLE = (
    "Trade-off cartography over the **blocking-OK** set only (intent-gate — **not L0 FEASIBLE**) — "
    "descriptive, intent-aware, never prescriptive."
)

DEFAULT_TAB = "1 · Setup & Run"

DECISION_STATES = [
    "Sample a new frontier",
    "Explore trade-offs on a plot",
    "Audit mechanisms & knees",
    "Export or hand off a point",
    "Run external optimizer / screening",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Setup & Run",
    DECISION_STATES[1]: "2 · Explore Frontier",
    DECISION_STATES[2]: "3 · Interpret & Audit",
    DECISION_STATES[3]: "4 · Export & Handoff",
    DECISION_STATES[4]: "5 · External Tools",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: "Pick **≥2 objectives** with explicit min/max. **Both (overlay)** doubles evaluations (Research + Reactor).",
    DECISION_STATES[1]: "Gray = hard-fail / blocking-fail shadow (plot-only). **Robust overlay** filters by min margin threshold — not physics change.",
    DECISION_STATES[2]: "Interaction matrix is **sign-only** on the blocking-OK manifold — '+' co-moves, '-' trade-off.",
    DECISION_STATES[3]: "Promotion copies decision variables only — evaluate in Point Designer before trusting margins.",
    DECISION_STATES[4]: "External optimizers **propose** inputs; SHAMS re-evaluates with frozen truth.",
}

PARETO_LOCK_LINE = (
    "**Pareto Lab is frozen** — trade-off cartography over blocking-OK (intent-gate) designs only — not L0 FEASIBLE. "
    "No optimization, relaxation, or recommendations. "
    "Labels say **Proposed — SHAMS-certified** — VERIFIED vs REJECTED with atlas on rejects; "
    "never a true minimum claim."
)

ROBUST_MARGIN_HELP = (
    "**Margin-robust overlay** filters Pareto points by `min_constraint_margin` ≥ threshold — "
    "a local blocking-OK margin cushion (not L0 FEASIBLE), not Phase+UQ uncertainty robustness "
    "(use External Tools for that)."
)

QUESTION_PRESETS = {
    "Where does robustness collapse?": {"color": "min_constraint_margin", "robust_only": True},
    "Where is q_div limiting?": {"color": "dominant_constraint", "show_failures": True},
    "Compare Reactor vs Research fronts": {"color": "intent", "intent_split": True},
    "Fusion power vs size": {"plot_x": "R0_m", "plot_y": "Pfus_total_MW"},
    "DT-adj fusion power vs size": {"plot_x": "R0_m", "plot_y": "Pfus_DT_adj_MW"},
}


def normalize_pareto_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in PARETO_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def teaching_banner(session) -> str | None:
    if not getattr(session, "pareto_teaching_mode", False):
        return None
    state = str(getattr(session, "pareto_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"
