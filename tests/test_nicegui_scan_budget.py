"""Scan Lab budget defaults and warnings."""
from __future__ import annotations

from ui_nicegui.session import DesignSession


def test_scan_cartography_defaults_within_11x11_budget() -> None:
    s = DesignSession()
    assert s.scan_cart_nx == 11
    assert s.scan_cart_ny == 11
    assert s.scan_cart_nx * s.scan_cart_ny <= 121
