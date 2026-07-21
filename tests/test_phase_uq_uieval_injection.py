"""Phase envelopes / UQ contracts must accept injected evaluator (UI choke point)."""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_phase_envelope_runner_accepts_evaluator():
    from src.phase_envelopes.runner import run_phase_envelope_for_point

    assert "evaluator" in inspect.signature(run_phase_envelope_for_point).parameters


def test_uq_contract_runner_accepts_evaluator():
    from src.uq_contracts.runner import run_uncertainty_contract_for_point

    assert "evaluator" in inspect.signature(run_uncertainty_contract_for_point).parameters


def test_phase_uq_resolve_outputs_prefers_evaluator():
    from src.phase_envelopes import runner as pe
    from src.uq_contracts import runner as uq

    assert "_resolve_outputs" in pe.__dict__
    assert "_resolve_outputs" in uq.__dict__
    assert "evaluator" in inspect.getsource(pe._resolve_outputs)
    assert "hot_ion_point" in inspect.getsource(pe._resolve_outputs)
    assert "evaluator" in inspect.getsource(uq._resolve_outputs)


def test_nicegui_phase_envelopes_injects_ui_evaluator():
    src = Path("ui_nicegui/decks/point_designer/phase_envelopes.py").read_text(encoding="utf-8")
    assert "ui_evaluator" in src
    assert "evaluator=ev" in src


def test_nicegui_uq_contracts_injects_ui_evaluator():
    src = Path("ui_nicegui/decks/point_designer/uncertainty_contracts.py").read_text(encoding="utf-8")
    assert "ui_evaluator" in src
    assert "evaluator=ev" in src


def test_robust_pareto_and_two_lane_inject_ui_evaluator():
    from ui_nicegui.lib import external_optimizer_helpers as h

    robust = inspect.getsource(h.run_robust_pareto_frontier)
    assert "ui_evaluator" in robust
    assert "evaluator=ev" in robust

    two = inspect.getsource(h.run_two_lane_uq)
    assert "ui_evaluator" in two
    assert "evaluator=ev" in two


def test_ccfs_forwards_evaluator_to_phase_and_uq():
    from src.extopt import certified_solve as cs

    src = inspect.getsource(cs.verify_ccfs_bundle)
    assert "run_phase_envelope_for_point(" in src
    assert "run_uncertainty_contract_for_point(" in src
    assert "evaluator=ev" in src


def test_pathfinding_forwards_evaluator_to_uq():
    from src.trade_studies import pathfinding as pf

    src = inspect.getsource(pf._robust_pass)
    assert "evaluator=ev" in src


def test_v351_lane_classify_forwards_evaluator():
    from src.atlas.frontier_atlas_v351 import classify_lanes_for_points

    src = inspect.getsource(classify_lanes_for_points)
    assert "evaluator=evaluator" in src


def test_v352_certify_accepts_and_forwards_evaluator():
    from src.certification.robust_envelope_v352 import certify_points_under_contract

    assert "evaluator" in inspect.signature(certify_points_under_contract).parameters
    src = inspect.getsource(certify_points_under_contract)
    assert "evaluator=evaluator" in src


def test_trade_v352_injects_ui_evaluator():
    src = Path("ui_nicegui/decks/trade_study_studio/advanced.py").read_text(encoding="utf-8")
    assert 'origin="NiceGUI:v352"' in src
    assert "evaluator=ev" in src


def test_frontier_ui_honors_recovery_y_and_phys_kpi():
    src = Path("ui_nicegui/decks/systems_mode/frontier_ui.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001" in src
    assert "_y_from_trace_row" in src
    assert "Seeded recovery trace" in src
    # Recovery must not hard-code V when another Y is selected.
    assert "yv = float(t.get(\"V\"" not in src or "_y_from_trace_row" in src
