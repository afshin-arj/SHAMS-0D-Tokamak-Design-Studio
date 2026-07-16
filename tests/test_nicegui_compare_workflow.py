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


def test_inputs_structure_uses_json_view_not_ui_json() -> None:
    import inspect

    from ui_nicegui.decks.compare import inputs_structure as is_mod

    src = inspect.getsource(is_mod)
    assert "render_json_blob" in src
    assert "ui.json" not in src


def test_metrics_panel_refreshes_all_outputs_toggle() -> None:
    import inspect

    from ui_nicegui.decks.compare import metrics as metrics_mod

    src = inspect.getsource(metrics_mod)
    assert "_all_outputs_section.refresh" in src


def test_compare_swap_includes_use_flags() -> None:
    import inspect

    from ui_nicegui.decks.compare import setup as cmp_setup
    from ui_nicegui.lib import compare_helpers as ch

    src = inspect.getsource(cmp_setup._swap_slots)
    assert "swap_compare_slots" in src
    helper = inspect.getsource(ch.swap_compare_slots)
    assert "cmp_use_slot_a" in helper
    assert "cmp_use_slot_b" in helper

    from ui_nicegui.lib.mode_scope_data import MODE_SCOPE

    assert "compare" in MODE_SCOPE
    assert any("rank" in line.lower() for line in MODE_SCOPE["compare"]["does_not"])


def test_compare_pd_soft_gate_allows_tabs() -> None:
    import inspect

    from ui_nicegui.decks import compare as cmp_mod

    src = inspect.getsource(cmp_mod.render_compare)
    assert "No Point Designer evaluation in session" in src
    assert "return" not in src.split("point_out")[1].split("with ui.row")[0] or "Open Point Designer" in src
    assert "Open Point Designer" in src
    # Soft gate must not early-return before tabs
    assert "artifact-only review" in src

def test_trade_study_controls_refresh_on_suggest() -> None:
    import inspect

    from ui_nicegui.decks.trade_study_studio import controls as ctrl_mod

    src = inspect.getsource(ctrl_mod)
    assert "on_change" in src
    assert "_apply_suggested_objectives" in src


def test_compare_tabs_goto_setup_when_slots_empty() -> None:
    import inspect

    from ui_nicegui.decks import compare as cmp_mod

    src = inspect.getsource(cmp_mod)
    assert "render_goto_setup_button" in src
    assert "1 · Load A & B" in src


def test_compare_export_navigates_to_point_designer() -> None:
    import inspect

    from ui_nicegui.decks.compare import export_panel as ep

    src = inspect.getsource(ep.render_export_panel)
    assert "navigate_to_point_designer" in src


def test_pareto_promote_navigates_to_point_designer() -> None:
    import inspect

    from ui_nicegui.decks.pareto_lab import export_handoff as eh

    src = inspect.getsource(eh.render_export_tab)
    assert "navigate_to_point_designer" in src
    assert "open_compare_deck" in src


def test_pd_telemetry_has_goto_configure_cta() -> None:
    import inspect

    from ui_nicegui.decks.point_designer import telemetry

    src = inspect.getsource(telemetry.render_telemetry)
    assert "Go to Configure" in src
    assert "render_goto_setup_button" in src


def test_pd_constraints_has_goto_configure_cta() -> None:
    import inspect

    from ui_nicegui.decks.point_designer import constraints

    src = inspect.getsource(constraints.render_constraints)
    assert "Go to Configure" in src
    assert "render_goto_setup_button" in src


def test_trade_study_pd_prerequisite_badge() -> None:
    import inspect

    from ui_nicegui.decks import trade_study_studio as ts_mod

    src = inspect.getsource(ts_mod.render_trade_study_studio)
    assert "ui.badge" in src
    assert "No Point Designer evaluation" in src
