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

# Expert navigation: workflow phases for fusion engineers implementing a design study.
HELM_NAV_GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "1 · Anchor a design point",
        "Define inputs and read the feasibility verdict under frozen truth.",
        ["Point Designer"],
    ),
    (
        "2 · Map and close",
        "Cartography across parameter space, then integrated systems closure.",
        ["Scan Lab", "Systems Mode"],
    ),
    (
        "3 · Compare and trade",
        "Artifact diffs, Pareto fronts, and certified trade studies.",
        ["Compare", "Pareto Lab", "Trade Study Studio"],
    ),
    (
        "4 · Develop concepts",
        "Compile intent, explore machine families, archive candidates.",
        ["Reactor Design Forge"],
    ),
    (
        "5 · Evidence and audit",
        "Constitutional benchmarks, batch suites, provenance, and export.",
        ["Publication Benchmarks", "System Suite", "Control Room"],
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
