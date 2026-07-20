"""Studio-wide guided/teaching mode carry-over across NiceGUI decks.

Deck ``*_teaching_mode`` flags must stay aligned so Guided banners do not
disagree after navigating between decks.
"""
from __future__ import annotations

from typing import Any, Iterable

TEACHING_MODE_ATTRS: tuple[str, ...] = (
    "systems_teaching_mode",
    "scan_teaching_mode",
    "pareto_teaching_mode",
    "trade_teaching_mode",
    "forge_teaching_mode",
    "suite_teaching_mode",
    "cmp_teaching_mode",
    "pub_teaching_mode",
    "cr_teaching_mode",
    "pd_teaching_mode",
)


def apply_guided_mode(session: Any, enabled: bool) -> None:
    """Set studio guided_mode and propagate to every deck teaching_mode flag."""
    on = bool(enabled)
    if hasattr(session, "guided_mode"):
        session.guided_mode = on
    for attr in TEACHING_MODE_ATTRS:
        if hasattr(session, attr):
            setattr(session, attr, on)


def sync_deck_guided_to_helm(session: Any, enabled: bool, *, deck_attr: str) -> None:
    """Deck Guided switch flipped — update that deck and studio-wide siblings."""
    apply_guided_mode(session, enabled)
    if hasattr(session, deck_attr):
        setattr(session, deck_attr, bool(enabled))


def teaching_mode_attrs() -> Iterable[str]:
    return TEACHING_MODE_ATTRS
