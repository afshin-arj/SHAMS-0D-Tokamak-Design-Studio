"""System Suite campaign → Point Designer promote honesty (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ui_nicegui.session import DesignSession


def test_promote_campaign_row_seeds_inputs_and_clears_pd_kpis():
    from ui_nicegui.lib.suite_helpers import promote_campaign_row_to_point_designer

    s = DesignSession()
    s.pd_last_outputs = {"Q_DT_eqv": 42.0, "verdict": "FEASIBLE"}
    s.pd_last_artifact = {"outputs": {"Q_DT_eqv": 42.0}}
    before_ip = float(s.inputs.get("Ip_MA", 0) or 0)
    s.suite_campaign_results_preview = [
        {
            "cid": "c0",
            "feasible_hard": False,
            "verdict": "INFEASIBLE",
            "inputs": {"Ip_MA": before_ip + 1.5, "R0_m": 6.1},
            "Q_DT_eqv": "— (diagnostic)",
        }
    ]
    n, feas = promote_campaign_row_to_point_designer(s, 0)
    assert n >= 2
    assert feas is False
    assert float(s.inputs["Ip_MA"]) == before_ip + 1.5
    assert float(s.inputs["R0_m"]) == 6.1
    assert s.pd_last_outputs is None
    assert s.pd_last_artifact is None


def test_promote_campaign_row_requires_preview():
    from ui_nicegui.lib.suite_helpers import promote_campaign_row_to_point_designer

    s = DesignSession()
    with pytest.raises(ValueError, match="campaign"):
        promote_campaign_row_to_point_designer(s, 0)


def test_suite_handoff_ui_wires_campaign_promote():
    src = Path("ui_nicegui/lib/suite_helpers.py").read_text(encoding="utf-8")
    assert "promote_campaign_row_to_point_designer" in src
    assert "suite-campaign-promote-pd" in src
    assert "navigate_to_point_designer" in src
    assert "invalidate_point_designer_after_seed" in src
    suite_init = Path("ui_nicegui/decks/system_suite/__init__.py").read_text(encoding="utf-8")
    assert "SUITE_RUNNING_ATTRS" in suite_init
    assert "refresh_tab_if_idle" in suite_init
