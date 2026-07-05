"""System Suite NiceGUI workflow and parity tests."""

from __future__ import annotations

from ui_nicegui.decks.system_suite import render_system_suite
from ui_nicegui.decks.system_suite import tabs as suite_tabs
from ui_nicegui.lib.suite_labels import (
    DECISION_TO_TAB,
    SUITE_TABS,
    normalize_suite_tab,
    teaching_banner,
)
from ui_nicegui.lib.suite_overlay_helpers import overlay_status_rows
from ui_nicegui.session import DesignSession


def test_normalize_suite_tab_legacy() -> None:
    assert normalize_suite_tab("Closure & Power") == "1 · Plant & Power"
    assert normalize_suite_tab("Authority · Exports · UQ") == "5 · Scenarios & Exports"


def test_suite_tabs_count() -> None:
    assert len(SUITE_TABS) == 5


def test_decision_maps_to_tab() -> None:
    for state, tab in DECISION_TO_TAB.items():
        assert tab in SUITE_TABS


def test_teaching_banner() -> None:
    s = DesignSession()
    assert teaching_banner(s) is None
    s.suite_teaching_mode = True
    assert teaching_banner(s) is not None


def test_overlay_status_rows() -> None:
    errors, warnings = overlay_status_rows({"magnet_error": "fail", "_authority_warnings": ["warn"]})
    assert len(errors) == 1
    assert warnings == ["warn"]


def test_suite_tab_renderers_import() -> None:
    assert callable(suite_tabs.render_tab_plant_power)
    assert callable(suite_tabs.render_tab_envelope_robustness)
    assert callable(render_system_suite)
