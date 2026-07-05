"""Point Designer Truth Console workflow labels and authority toggles."""
from __future__ import annotations

from ui_nicegui.lib.pd_authority_toggles import (
    AUTHORITY_OVERLAY_TOGGLES,
    AUTHORITY_TOGGLE_KEYS,
    count_enabled,
    default_overlay_bool,
    reactor_intent_hint,
)
from ui_nicegui.lib.pd_workflow_labels import (
    DECISION_STATES,
    DECISION_TO_TAB,
    PD_TRUTH_TABS,
    TAB_HELP,
    normalize_pd_tab,
    teaching_banner,
)
from ui_nicegui.session import DesignSession


def test_pd_workflow_tabs_complete() -> None:
    assert len(PD_TRUTH_TABS) == 3
    for tab in PD_TRUTH_TABS:
        assert tab in TAB_HELP


def test_normalize_pd_tab_legacy() -> None:
    assert normalize_pd_tab("Configure") == "1 · Configure"
    assert normalize_pd_tab("2 · Telemetry") == "2 · Telemetry"
    assert normalize_pd_tab("unknown") == "1 · Configure"


def test_decision_routes_to_tab() -> None:
    assert DECISION_TO_TAB[DECISION_STATES[2]] == "2 · Telemetry"
    assert DECISION_TO_TAB[DECISION_STATES[3]] == "3 · Constraints"


def test_teaching_banner_guided() -> None:
    s = DesignSession()
    s.pd_teaching_mode = True
    s.pd_decision_state = DECISION_STATES[1]
    assert "Evaluate Point" in teaching_banner(s)
    s.pd_teaching_mode = False
    assert teaching_banner(s) == ""


def test_authority_toggle_defaults_reactor() -> None:
    s = DesignSession()
    s.design_intent = "Power Reactor (net-electric)"
    overlay = {}
    for key, _, _ in AUTHORITY_OVERLAY_TOGGLES:
        overlay[key] = default_overlay_bool(overlay, key, s.design_intent)
    enabled, total = count_enabled(overlay)
    assert total == len(AUTHORITY_TOGGLE_KEYS)
    assert enabled >= 0
    assert "tritium" in reactor_intent_hint(s.design_intent).lower()


def test_authority_toggle_keys_match_dashboard() -> None:
    assert len(AUTHORITY_OVERLAY_TOGGLES) == 12
    assert AUTHORITY_TOGGLE_KEYS == [t[0] for t in AUTHORITY_OVERLAY_TOGGLES]
