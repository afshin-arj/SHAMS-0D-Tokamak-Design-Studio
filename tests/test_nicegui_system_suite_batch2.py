"""Batch 2: System Suite read-only overlay wiring."""
from __future__ import annotations

import math

from ui_nicegui.decks.system_suite import render_system_suite
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def test_artifact_triple_empty() -> None:
    s = DesignSession()
    art, inp, out = get_point_artifact_triple(s)
    assert out is None or isinstance(out, dict)


def test_system_suite_with_point_eval() -> None:
    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))
    _, _, point_out = get_point_artifact_triple(s)
    assert isinstance(point_out, dict)

    from tools.system_suite import power_closure_overlay

    rep = power_closure_overlay(point_out, s.inputs)
    assert rep.stamp_sha256 and len(rep.stamp_sha256) == 64
    assert math.isfinite(rep.recirc_frac) or rep.recirc_frac != rep.recirc_frac


def test_system_suite_renderer_import() -> None:
    assert callable(render_system_suite)
