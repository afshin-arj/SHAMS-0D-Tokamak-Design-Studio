"""Plain-language System Suite labels — workflow tabs for fusion experts."""

from __future__ import annotations

SUITE_TABS = [
    "1 · Plant & Power",
    "2 · Operations & Thermal",
    "3 · Lifetime & Regimes",
    "4 · Envelope Robustness",
    "5 · Scenarios & Exports",
]

_LEGACY_TAB_MAP = {
    "Closure & Power": "1 · Plant & Power",
    "Ops · Thermal · Trajectory": "2 · Operations & Thermal",
    "Lifetime · Fuel · Regimes": "3 · Lifetime & Regimes",
    "Phase Envelopes": "4 · Envelope Robustness",
    "Profile Contracts": "4 · Envelope Robustness",
    "Authority · Exports · UQ": "5 · Scenarios & Exports",
}

TAB_HELP = {
    "1 · Plant & Power": "Net-electric closure and recirculation ledger from the evaluated point.",
    "2 · Operations & Thermal": "Duty-cycle delivery, thermal trace, and pulse power envelope on frozen L0.",
    "3 · Lifetime & Regimes": "First-wall dose, cycle budgets, tritium margins, and operating regime labels.",
    "4 · Envelope Robustness": "Outer-loop screening: time phases, profile corners, or input intervals — pick the question first.",
    "5 · Scenarios & Exports": "Scenario libraries, campaign bundles, and benchmark parity packs.",
}

DECK_SUBTITLE = (
    "L0-anchored system overlays on the last Point Designer evaluation — "
    "same inputs, same frozen truth."
)

DEFAULT_TAB = "1 · Plant & Power"

DECISION_STATES = [
    "Plant closure & duty",
    "Thermal & pulse trajectory",
    "Lifetime, fuel & regimes",
    "Envelope robustness (phase / profile / UQ)",
    "Scenarios & external exports",
]

DECISION_TO_TAB = {
    DECISION_STATES[0]: "1 · Plant & Power",
    DECISION_STATES[1]: "2 · Operations & Thermal",
    DECISION_STATES[2]: "3 · Lifetime & Regimes",
    DECISION_STATES[3]: "4 · Envelope Robustness",
    DECISION_STATES[4]: "5 · Scenarios & Exports",
}

TEACHING_HINTS = {
    DECISION_STATES[0]: "Start here for **net electric** and recirculation — confirms plant closure at the evaluated point.",
    DECISION_STATES[1]: "Use **availability sensitivity** to scale duty; thermal and trajectory panels are diagnostic traces only.",
    DECISION_STATES[2]: "Check **first-wall dpa**, **pulse cycles**, and **TBR** before envelope or export work.",
    DECISION_STATES[3]: "**Phase envelope** = ramp/flat-top phases; **profile corners** = transport/profile library; **UQ intervals** = input uncertainty corners.",
    DECISION_STATES[4]: "Scenario presets, optimizer campaign packs, and benchmark parity — all stamped and external to L0 truth.",
}

ENVELOPE_ROUTER = (
    "**Which tool?** **Phase envelope** — feasibility vs ramp / flat-top / ramp-down. "
    "**Profile corners** — certified profile & transport envelopes. "
    "**Uncertainty intervals** — feasibility across declared input ranges (2^N corners)."
)


def normalize_suite_tab(step: str) -> str:
    s = str(step or DEFAULT_TAB).strip()
    if s in SUITE_TABS:
        return s
    return _LEGACY_TAB_MAP.get(s, DEFAULT_TAB)


def teaching_banner(session) -> str | None:
    if not getattr(session, "suite_teaching_mode", False):
        return None
    state = str(getattr(session, "suite_decision_state", DECISION_STATES[0]))
    hint = TEACHING_HINTS.get(state, TEACHING_HINTS[DECISION_STATES[0]])
    return f"**Guided mode — {state}:** {hint}"
