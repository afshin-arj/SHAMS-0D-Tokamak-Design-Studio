"""Cross-deck navigation hook (registered by app.py on startup)."""
from __future__ import annotations

from typing import Callable, Optional

_deck_change: Optional[Callable[[str], None]] = None
_helm_refresh: Optional[Callable[[], None]] = None
_helm_settings_refresh: Optional[Callable[[], None]] = None
_status_refresh: Optional[Callable[[], None]] = None
_deck_refresh: Optional[Callable[[], None]] = None


def register_deck_change(callback: Callable[[str], None]) -> None:
    global _deck_change
    _deck_change = callback


def register_helm_refresh(callback: Callable[[], None]) -> None:
    """Lightweight refresh after deck switch (nav + compass only)."""
    global _helm_refresh
    _helm_refresh = callback


def register_helm_settings_refresh(callback: Callable[[], None]) -> None:
    """Full Helm settings panel (session setup, DSG, chronicle)."""
    global _helm_settings_refresh
    _helm_settings_refresh = callback


def register_status_refresh(callback: Callable[[], None]) -> None:
    global _status_refresh
    _status_refresh = callback


def register_deck_refresh(callback: Callable[[], None]) -> None:
    """Re-render active deck without changing active_deck (e.g. PD subdeck toggle)."""
    global _deck_refresh
    _deck_refresh = callback


def switch_deck(name: str) -> None:
    if _deck_change is not None:
        _deck_change(name)


def refresh_helm() -> None:
    if _helm_refresh is not None:
        _helm_refresh()


def refresh_helm_settings() -> None:
    if _helm_settings_refresh is not None:
        _helm_settings_refresh()


def refresh_status() -> None:
    if _status_refresh is not None:
        _status_refresh()


def refresh_active_deck() -> None:
    if _deck_refresh is not None:
        _deck_refresh()
