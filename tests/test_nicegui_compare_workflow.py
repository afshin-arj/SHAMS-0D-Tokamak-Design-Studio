"""Compare deck workflow tests."""
from __future__ import annotations

import json

from ui_nicegui.decks.compare import render_compare
from ui_nicegui.decks.compare.setup import resolve_artifacts
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.compare_helpers import (
    artifact_from_point,
    comparison_json_bundle,
    comparison_markdown,
    constraint_margin_diff_rows,
    input_diff_rows,
    metric_diff_rows,
    normalize_compare_artifact,
    numeric_output_diff_rows,
    summarize_comparison,
)
from ui_nicegui.lib.compare_labels import (
    COMPARE_TABS,
    DECISION_TO_TAB,
    normalize_compare_tab,
)
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.session import DesignSession


def test_compare_renderer_import() -> None:
    assert callable(render_compare)


def test_compare_tabs_and_labels() -> None:
    assert len(COMPARE_TABS) == 5
    assert normalize_compare_tab("Key metrics") == "2 · Performance"
    assert DECISION_TO_TAB["Load baseline vs variant"] == "1 · Load A & B"


def test_metric_diff_rows() -> None:
    a = {"outputs": {"Q_DT_eqv": 10.0, "P_e_net_MW": 100.0}}
    b = {"outputs": {"Q_DT_eqv": 12.0, "P_e_net_MW": 90.0}}
    rows = metric_diff_rows(a, b)
    q_row = next(r for r in rows if r["metric"] == "Q_DT_eqv")
    assert float(q_row["B-A"]) == 2.0


def test_input_and_output_diffs() -> None:
    a = {"inputs": {"R0_m": 1.8}, "outputs": {"Q": 1.0, "betaN": 1.0}}
    b = {"inputs": {"R0_m": 2.0}, "outputs": {"Q": 1.5, "betaN": 2.1}}
    assert len(input_diff_rows(a, b)) == 1
    out = numeric_output_diff_rows(a, b)
    assert any(r["metric"] == "Q" for r in out)
    assert any(r["metric"] == "betaN" for r in out)


def test_constraint_margin_diff_new_failure() -> None:
    a = {"constraints": [{"name": "q95", "failed": False, "margin": 0.2, "passed": True}]}
    b = {"constraints": [{"name": "q95", "failed": True, "margin": -0.1, "passed": False}]}
    rows = constraint_margin_diff_rows(a, b)
    assert rows[0]["new_failure"] is True


def test_summarize_comparison() -> None:
    s = DesignSession()
    out_a = ui_evaluate(s.build_point_inputs(), origin="test")
    set_point_evaluation(s, outputs=out_a, inputs=dict(s.inputs))
    art_a = artifact_from_point(s)
    inp_b = dict(s.inputs)
    inp_b["Paux_MW"] = float(s.inputs.get("Paux_MW", 50.0)) + 10.0
    s.inputs.update(inp_b)
    out_b = ui_evaluate(s.build_point_inputs(), origin="test")
    art_b = normalize_compare_artifact({"outputs": out_b, "inputs": inp_b, "label": "variant"})
    summary = summarize_comparison(art_a, art_b)
    assert summary["loaded"] is True
    assert summary["verdict_a"] in ("FEASIBLE", "INFEASIBLE")


def test_comparison_exports() -> None:
    a = {"outputs": {"Q": 1.0}, "constraints": [{"name": "q95", "residual": -0.1}]}
    b = {"outputs": {"Q": 2.0}, "constraints": [{"name": "q95", "residual": 0.2}]}
    md = comparison_markdown(a, b)
    assert "SHAMS Artifact Comparison" in md
    bundle = comparison_json_bundle(a, b)
    assert "key_metrics" in bundle
    json.dumps(bundle)


def test_resolve_artifacts_session() -> None:
    s = DesignSession()
    s.cmp_slot_a = {"outputs": {"Q": 1.0}}
    s.cmp_slot_b = {"outputs": {"Q": 2.0}}
    a, b = resolve_artifacts(s)
    assert a and b
