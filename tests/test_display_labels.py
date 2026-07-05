"""Tests for display_labels normalization."""
from __future__ import annotations

from ui_nicegui.lib.display_labels import (
    DECK_FRONTIER_ATLAS,
    authority_display,
    normalize_user_label,
    strip_version_tags,
)


def test_strip_version_tags_paren() -> None:
    assert strip_version_tags("Robust Cert (v352)") == "Robust Cert"
    assert strip_version_tags("v204: Timeline strip") == "Timeline strip"


def test_legacy_alias() -> None:
    assert normalize_user_label("Multi-Objective Feasible Frontier Atlas (v351)") == DECK_FRONTIER_ATLAS


def test_authority_display() -> None:
    assert authority_display("v389") == "Structural stress authority"
    assert authority_display("389") == "Structural stress authority"
