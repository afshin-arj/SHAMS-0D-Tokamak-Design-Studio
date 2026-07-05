"""Helm Console labels — design intents, navigation groups, section titles."""
from __future__ import annotations

from ui_nicegui.decks.labels import DECK_LABELS

# Four intents matching configure_governance.py (expanded covenant vs Streamlit sidebar).
DESIGN_INTENT_OPTIONS: list[str] = [
    "Power Reactor (net-electric)",
    "Experimental Device (research)",
    "Pilot Plant (demonstration)",
    "High-field science (HFS)",
]

# Expert navigation: (group title, help caption, deck names from DECK_LABELS).
HELM_NAV_GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "Frozen truth",
        "Evaluate one operating point; read verdict-first telemetry.",
        ["Point Designer"],
    ),
    (
        "Exploration engines",
        "Systems solves, parameter scans, Pareto fronts, and trade studies.",
        ["Systems Mode", "Scan Lab", "Pareto Lab", "Trade Study Studio"],
    ),
    (
        "Concept forge",
        "Compile design intent and explore reactor concept families.",
        ["Reactor Design Forge"],
    ),
    (
        "Evidence & audit",
        "Batch campaigns, artifact compare, publication benchmarks, and governance.",
        ["System Suite", "Compare", "Publication Benchmarks", "Control Room"],
    ),
]

# Plain-language section titles: legacy Streamlit sidebar names → expert-friendly labels.
HELM_SECTION_LABELS: dict[str, str] = {
    "Helm Console - Expert Navigation": "Helm Console",
    "Captain's Ledger": "Session posture",
    "Captain\u2019s Ledger": "Session posture",
    "Explain mode (show equations & reasons)": "Explain mode",
    "Advanced controls": "Advanced controls",
    "Reactor Covenant": "Reactor covenant",
    "Integrity Gate - Requirements & Health": "Integrity gate",
    "Integrity Gate": "Integrity gate",
    "Technology Readiness (TRL Contracts)": "Technology readiness",
    "Benchmark Vault": "Benchmark vault",
    "Black-Box Chronicle": "Activity chronicle",
    "Navigation": "Deck navigation",
    "Design Contract": "Design contract",
    "Reference Context": "Reference context",
    "Evidence Log": "Evidence log",
    "Session & Authority": "Session & authority",
}


def helm_section_label(streamlit_name: str) -> str:
    """Return expert-friendly label for a Streamlit sidebar section name."""
    return HELM_SECTION_LABELS.get(streamlit_name, streamlit_name)


def assert_nav_groups_cover_decks() -> None:
    """Sanity check: every registered deck appears in exactly one nav group."""
    seen: list[str] = []
    for _, _, decks in HELM_NAV_GROUPS:
        seen.extend(decks)
    assert set(seen) == set(DECK_LABELS), f"HELM_NAV_GROUPS mismatch: {set(DECK_LABELS) ^ set(seen)}"


assert_nav_groups_cover_decks()
