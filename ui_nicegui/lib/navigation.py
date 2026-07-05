"""Cross-deck navigation hook (registered by app.py on startup)."""
from __future__ import annotations

from typing import Callable, Optional

_deck_change: Optional[Callable[[str], None]] = None
_helm_refresh: Optional[Callable[[], None]] = None
_status_refresh: Optional[Callable[[], None]] = None


def register_deck_change(callback: Callable[[str], None]) -> None:
    global _deck_change
    _deck_change = callback


def register_helm_refresh(callback: Callable[[], None]) -> None:
    global _helm_refresh
    _helm_refresh = callback


def register_status_refresh(callback: Callable[[], None]) -> None:
    global _status_refresh
    _status_refresh = callback


def switch_deck(name: str) -> None:
    if _deck_change is not None:
        _deck_change(name)


def refresh_helm() -> None:
    if _helm_refresh is not None:
        _helm_refresh()


def refresh_status() -> None:
    if _status_refresh is not None:
        _status_refresh()
