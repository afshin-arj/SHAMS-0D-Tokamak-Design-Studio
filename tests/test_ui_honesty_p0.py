"""P0 UI honesty fixes: q_div/P_SOL taxonomy, v404 toggle wiring, v396 spread cap."""
from __future__ import annotations

import math

import pytest


def test_regime_compass_qdiv_and_psol_are_proxy() -> None:
    from ui_nicegui.lib.pd_parity_helpers import regime_compass_rows

    rows = {r["key"]: r for r in regime_compass_rows({})}
    assert rows["q_div_MW_m2"]["type"] == "Proxy"
    assert rows["P_SOL_over_R_MW_m"]["type"] == "Proxy"


def test_policy_caption_research_qdiv_physics_unchanged() -> None:
    from ui_nicegui.lib.pd_intent_policy import policy_caption

    cap = policy_caption("Experimental Device (research)")
    assert "Research" in cap
    assert "q95" in cap
    assert "does not change q_div physics" in cap
    assert "demotes" in cap
    # Pilot / HFS captions unchanged
    assert "Pilot" in policy_caption("Pilot Plant (demonstration)")
    assert "High-field" in policy_caption("High-field science (HFS)")


def test_authority_toggles_use_real_v404_schema_key() -> None:
    from ui_nicegui.lib.pd_authority_toggles import AUTHORITY_TOGGLE_KEYS

    assert "include_structural_life_v404" in AUTHORITY_TOGGLE_KEYS
    assert "include_structural_life_authority_v404" not in AUTHORITY_TOGGLE_KEYS


def test_streamlit_authority_dashboard_uses_real_v404_key() -> None:
    pytest.importorskip("streamlit")
    from ui.authority_dashboard import _OVERLAY_TOGGLES_FIELDS

    assert "include_structural_life_v404" in _OVERLAY_TOGGLES_FIELDS
    assert "include_structural_life_authority_v404" not in _OVERLAY_TOGGLES_FIELDS


def test_overlay_group_specs_no_duplicate_v404_entry() -> None:
    from ui_nicegui.lib.pd_panel_labels import OVERLAY_GROUP_SPECS

    keys = [k for _, items in OVERLAY_GROUP_SPECS for k, _ in items]
    assert keys.count("include_structural_life_v404") == 1
    assert "include_structural_life_authority_v404" not in keys


def test_merge_overlay_aliases_legacy_v404_key() -> None:
    from ui_nicegui.lib.point_inputs_builder import build_point_inputs
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.overlay["include_structural_life_authority_v404"] = True
    inp = build_point_inputs(s)
    assert bool(getattr(inp, "include_structural_life_v404", False)) is True


def test_v396_spread_knob_optional_min_one() -> None:
    from ui_nicegui.lib.pd_overlay_knobs import OVERLAY_NUMERIC_PANELS, _OPTIONAL_CAP_KNOBS

    fields = dict(OVERLAY_NUMERIC_PANELS)["include_transport_envelope_v396"]
    entry = next(f for f in fields if f[0] == "transport_spread_max_v396")
    _, label, default, lo, hi, _ = entry
    assert math.isnan(default)  # schema default: cap off
    assert lo >= 1.0
    assert hi <= 20.0
    assert "optional" in label.lower()
    assert "transport_spread_max_v396" in _OPTIONAL_CAP_KNOBS


def test_regime_compass_q95_is_proxy() -> None:
    from ui_nicegui.lib.pd_parity_helpers import regime_compass_rows

    rows = {r["key"]: r for r in regime_compass_rows({})}
    assert rows["q95_proxy"]["type"] == "Proxy"


def test_deck_nav_disambiguates_systems_mode_vs_suite() -> None:
    from ui_nicegui.lib.deck_workflow import deck_nav_short_label

    assert "Close" in deck_nav_short_label("Systems Mode")
    assert "L1" in deck_nav_short_label("System Suite")
