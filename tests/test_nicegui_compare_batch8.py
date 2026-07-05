"""Batch 8: Compare deck wiring."""
from __future__ import annotations

from ui_nicegui.decks.compare import render_compare
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.compare_helpers import (
    artifact_from_point,
    comparison_markdown,
    metric_diff_rows,
    normalize_compare_artifact,
    summarize_comparison,
)
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def test_compare_renderer_import() -> None:
    assert callable(render_compare)


def test_metric_diff_rows() -> None:
    a = {"outputs": {"Q_DT_eqv": 10.0, "P_e_net_MW": 100.0}}
    b = {"outputs": {"Q_DT_eqv": 12.0, "P_e_net_MW": 90.0}}
    rows = metric_diff_rows(a, b)
    assert any(r["metric"] == "Q_DT_eqv" for r in rows)
    q_row = next(r for r in rows if r["metric"] == "Q_DT_eqv")
    assert float(q_row["B-A"]) == 2.0


def test_summarize_comparison() -> None:
    s = DesignSession()
    out_a = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out_a, inputs=dict(s.inputs))
    art_a = artifact_from_point(s)
    assert isinstance(art_a, dict)
    inp_b = dict(s.inputs)
    inp_b["Paux_MW"] = float(s.inputs.get("Paux_MW", 50.0)) + 10.0
    s.inputs.update(inp_b)
    out_b = ui_evaluate(s.build_point_inputs(), origin="test")
    art_b = normalize_compare_artifact({"outputs": out_b, "inputs": inp_b, "label": "variant"})
    summary = summarize_comparison(art_a, art_b)
    assert summary["loaded"] is True
    assert summary["verdict_a"] in ("FEASIBLE", "INFEASIBLE")


def test_comparison_markdown() -> None:
    a = {"outputs": {"Q": 1.0}, "constraints": [{"name": "q95", "residual": -0.1}]}
    b = {"outputs": {"Q": 2.0}, "constraints": [{"name": "q95", "residual": 0.2}]}
    md = comparison_markdown(a, b)
    assert "SHAMS Artifact Comparison" in md
    assert "q95" in md
