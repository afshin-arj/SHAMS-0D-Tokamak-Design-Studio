"""Batch 1: Point Designer input builder and evaluate wiring."""
from __future__ import annotations

from ui_nicegui.lib.point_inputs_builder import build_point_inputs
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def test_build_point_inputs_core_fields() -> None:
    s = DesignSession()
    inp = build_point_inputs(s)
    assert float(inp.R0_m) == 1.81
    assert float(inp.Ip_MA) == 8.0
    assert str(inp.magnet_technology) == "HTS_REBCO"


def test_verdict_summary_empty() -> None:
    assert verdict_summary({})["loaded"] is False


def test_verdict_summary_after_eval() -> None:
    from ui_nicegui.evaluate import ui_evaluate

    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    summary = verdict_summary(out)
    assert summary["loaded"] is True
    assert summary["verdict"] in ("FEASIBLE", "INFEASIBLE")
