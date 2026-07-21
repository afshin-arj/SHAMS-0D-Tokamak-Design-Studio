"""Suite/Pareto NiceGUI choke-point injection + plant-KPI honesty."""
from __future__ import annotations

import inspect
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_evaluator_bridge_override_routes_calls():
    from src.solvers.evaluator_bridge import evaluate_point, set_evaluate_point_override

    calls = {"n": 0}

    def _ov(inp, *, origin="solver", Paux_for_Q_MW=None, **kw):
        calls["n"] += 1
        return {"Q_DT_eqv": 1.0, "origin": origin, "Paux_for_Q_MW": Paux_for_Q_MW}

    set_evaluate_point_override(_ov)
    try:
        out = evaluate_point(object(), origin="test_override", Paux_for_Q_MW=12.0)  # type: ignore[arg-type]
        assert calls["n"] == 1
        assert out.get("origin") == "test_override"
        assert out.get("Paux_for_Q_MW") == 12.0
    finally:
        set_evaluate_point_override(None)


def test_campaign_eval_accepts_injected_evaluator():
    from src.campaign.eval import evaluate_campaign_candidates

    src = inspect.getsource(evaluate_campaign_candidates)
    assert "evaluator" in src
    assert "Evaluator(label=" in src  # fallback retained


def test_suite_helpers_inject_ui_evaluator():
    from ui_nicegui.lib import suite_extended_helpers as h
    from ui_nicegui.lib import pareto_helpers as ph

    assert "ui_evaluator" in inspect.getsource(h.evaluate_campaign_batch)
    assert "ui_evaluator" in inspect.getsource(h.run_parity_suite)
    assert "set_evaluate_point_override" in inspect.getsource(ph.run_pareto_study)
    assert "ui_evaluate" in inspect.getsource(ph.run_pareto_study)


def test_suite_ops_thermal_watermarks_plant_kpis():
    from ui_nicegui.decks.system_suite import tabs

    src = inspect.getsource(tabs.render_tab_ops_thermal)
    assert "claim_allowed" in src
    assert "diagnostic" in src.lower()
    assert "plant_kpi_honesty_for_point" in src


def test_profile_contracts_accepts_evaluator_kwarg():
    from src.analysis.profile_contracts_v362 import evaluate_profile_contracts_v362

    sig = inspect.signature(evaluate_profile_contracts_v362)
    assert "evaluator" in sig.parameters


def test_parity_runner_accepts_evaluator_kwarg():
    from src.parity_harness.runner import run_benchmark_suite, run_suite

    assert "evaluator" in inspect.signature(run_suite).parameters
    assert "evaluator" in inspect.signature(run_benchmark_suite).parameters
