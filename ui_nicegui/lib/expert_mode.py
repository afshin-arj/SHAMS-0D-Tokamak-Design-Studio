"""Helm expert-mode carry-over across NiceGUI decks.

Helm ``expert_mode`` is the studio-wide switch. Deck ``*_expert_view`` flags
must stay aligned so solver/forensics panels do not disagree with Helm.
"""
from __future__ import annotations

from typing import Any, Iterable

# Deck-local expert toggles that must mirror Helm ``expert_mode``.
EXPERT_VIEW_ATTRS: tuple[str, ...] = (
    "systems_expert_view",
    "scan_expert_view",
    "pareto_expert_view",
    "trade_expert_view",
    "forge_expert_view",
    "suite_expert_view",
    "cmp_expert_view",
    "pub_expert_view",
    "cr_expert_view",
    "pd_expert_view",
)


def apply_expert_mode(session: Any, enabled: bool) -> None:
    """Set Helm expert_mode and propagate to every deck expert_view flag."""
    on = bool(enabled)
    session.expert_mode = on
    for attr in EXPERT_VIEW_ATTRS:
        if hasattr(session, attr):
            setattr(session, attr, on)


def sync_deck_expert_to_helm(session: Any, enabled: bool, *, deck_attr: str) -> None:
    """Deck switch flipped — update that deck flag and studio-wide expert_mode + siblings."""
    apply_expert_mode(session, enabled)
    # apply_expert_mode already set all attrs; keep deck_attr explicit for callers.
    if hasattr(session, deck_attr):
        setattr(session, deck_attr, bool(enabled))


def expert_view_attrs() -> Iterable[str]:
    return EXPERT_VIEW_ATTRS
