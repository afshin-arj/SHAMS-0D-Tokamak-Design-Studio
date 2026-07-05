"""Plain-language Publication Benchmarks labels — workflow for fusion experts."""

from __future__ import annotations

from ui_nicegui.lib.display_labels import TAB_EVIDENCE_PACK

PUB_WORKFLOW_TABS = [
    "1 · Constitutional Atlas",
    "2 · Publication Pack",
    "3 · Cross-Code Parity",
    "4 · Governance & Contracts",
    "5 · Evidence Export",
]

_LEGACY_TAB_MAP = {
    "Tokamak Constitutional Atlas": "1 · Constitutional Atlas",
    "Cross-Code Constitutions": "3 · Cross-Code Parity",
    "Cross‑Code Constitutions": "3 · Cross-Code Parity",
    "Publication Benchmarks": "2 · Publication Pack",
    "Contract Studio": "4 · Governance & Contracts",
    "Regulatory Evidence Pack Builder": "5 · Evidence Export",
    TAB_EVIDENCE_PACK: "5 · Evidence Export",
}

TAB_HELP = {
    "1 · Constitutional Atlas": (
        "Evaluate famous tokamak presets under Research or Reactor intent — "
        "constitution diff, local fragility scan, deterministic evidence JSON."
    ),
    "2 · Publication Pack": (
        "Batch-generate paper-ready CSV/JSON tables for configured reference machines. "
        "Audit-grade; uses frozen Point Designer only."
    ),
    "3 · Cross-Code Parity": (
        "Map external system-code clause semantics against SHAMS intent constitutions. "
        "Documentation-level; does not execute external codes."
    ),
    "4 · Governance & Contracts": (
        "Validate governance contracts, export contract bundles, and build "
        "reviewer / licensing ZIP packs from the current session artifact."
    ),
    "5 · Evidence Export": (
        "Hash-locked session evidence ZIP from cached runs (Point Designer, Scan, Pareto, …). "
        "Export-only — no physics recomputation."
    ),
}

DECK_SUBTITLE = (
    "Reviewer-safe constitutional benchmarks and publication tables on the frozen evaluator — "
    "preset-driven, intent-aware, deterministic exports."
)

DEFAULT_TAB = "1 · Constitutional Atlas"

DECISION_STATES = [
    "Benchmark a tokamak preset (ITER, SPARC, …)",
    "Generate publication tables for machines",
    "Compare SHAMS vs external code semantics",
    "Validate contracts & governance packs",
    "Export session evidence for reviewers",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Constitutional Atlas",
    DECISION_STATES[1]: "2 · Publication Pack",
    DECISION_STATES[2]: "3 · Cross-Code Parity",
    DECISION_STATES[3]: "4 · Governance & Contracts",
    DECISION_STATES[4]: "5 · Evidence Export",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: (
        "**Research** vs **Reactor** changes which constraints are blocking. "
        "Constitution diff shows semantic changes vs the preset's native intent."
    ),
    DECISION_STATES[1]: (
        "Acknowledge the audit-grade run, then inspect topology fractions and "
        "explain delta vs a baseline pack when the run succeeds."
    ),
    DECISION_STATES[2]: (
        "Pick an external code record and SHAMS intent; clause table shows side-by-side semantics."
    ),
    DECISION_STATES[3]: (
        "Contract Studio validates `contracts/` JSON. Reviewer and licensing packs need a "
        "session run artifact from Point Designer or Systems Mode."
    ),
    DECISION_STATES[4]: (
        "Select which cached session sources to include. Missing sources are shown but disabled."
    ),
}


def normalize_pub_tab(tab: str | None) -> str:
    if not tab:
        return DEFAULT_TAB
    t = str(tab).strip()
    if t in PUB_WORKFLOW_TABS:
        return t
    return _LEGACY_TAB_MAP.get(t, DEFAULT_TAB)


def teaching_banner(session) -> str:
    if not getattr(session, "pub_teaching_mode", True):
        return ""
    state = getattr(session, "pub_decision_state", "") or DECISION_STATES[0]
    return TEACHING_HINTS.get(state, "")
