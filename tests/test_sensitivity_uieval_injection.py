"""Sensitivity / forensics NiceGUI choke-point injection tests."""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_local_sensitivities_exists_and_defaults_to_bridge():
    from src.solvers.sensitivity import local_sensitivities

    src = inspect.getsource(local_sensitivities)
    assert "evaluate_point" in src or "_default_evaluator" in inspect.getsource(
        __import__("src.solvers.sensitivity", fromlist=["_default_evaluator"])
    )
    mod = Path("src/solvers/sensitivity.py").read_text(encoding="utf-8")
    assert "hot_ion_point" not in mod or "Never calls bare" in mod
    assert "def local_sensitivities" in mod
    assert "evaluate_point" in mod


def test_solvers_sensitivity_no_bare_hot_ion_call():
    mod = Path("src/solvers/sensitivity.py").read_text(encoding="utf-8")
    assert "from physics.hot_ion import" not in mod
    assert "hot_ion_point(" not in mod


def test_analysis_sensitivity_uses_resolve_outputs():
    from src.analysis import sensitivity as sens

    assert "evaluate_fn" in inspect.signature(sens.deterministic_sensitivity_pack).parameters
    assert "hot_ion_point(" not in Path(sens.__file__).read_text(encoding="utf-8")
    assert "_resolve_outputs" in sens.__dict__


def test_forensics_accepts_evaluate_fn():
    from src.analysis.forensics import local_sensitivity

    assert "evaluate_fn" in inspect.signature(local_sensitivity).parameters
    src = Path("src/analysis/forensics.py").read_text(encoding="utf-8")
    assert "hot_ion_point(" not in src
    assert "evaluate_point" in src


def test_systems_tools_ui_uses_ui_evaluate():
    src = Path("ui_nicegui/decks/systems_mode/tools_ui.py").read_text(encoding="utf-8")
    assert "ui_evaluate" in src
    assert "local_sensitivities" in src
    assert "PHYS-KPI-001" in src


def test_cr_sensitivity_injects_ui_evaluate():
    from ui_nicegui.lib import cr_chronicle_helpers as h

    assert "ui_evaluate" in inspect.getsource(h.run_sensitivity_pack)
    assert "evaluate_fn=_eval" in inspect.getsource(h.run_sensitivity_pack)
    assert "ui_evaluate" in inspect.getsource(h.run_local_forensics)


def test_pd_forensics_injects_ui_evaluate():
    from ui_nicegui.lib import pd_forensics_helpers as h

    assert "ui_evaluate" in inspect.getsource(h.run_local_forensics)


def test_pd_notify_warns_on_infeasible_complete():
    src = Path("ui_nicegui/decks/point_designer/__init__.py").read_text(encoding="utf-8")
    assert "point is INFEASIBLE" in src
    assert 'type="warning"' in src


def test_local_sensitivities_runs_with_fake_evaluator():
    from src.models.inputs import PointInputs
    from src.solvers.sensitivity import local_sensitivities

    base = PointInputs(
        R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0
    )
    calls = {"n": 0}

    def _ev(inp):
        calls["n"] += 1
        return {"Q_DT_eqv": float(getattr(inp, "Ip_MA", 0.0)), "H98": 1.0}

    sens = local_sensitivities(base, params=["Ip_MA"], outputs=["Q_DT_eqv"], evaluator=_ev, h=0.1)
    assert calls["n"] >= 3  # base + plus + minus (base counted in FD)
    assert "Q_DT_eqv" in sens
    assert "Ip_MA" in sens["Q_DT_eqv"]
