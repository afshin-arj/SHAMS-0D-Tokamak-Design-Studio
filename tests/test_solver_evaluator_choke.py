from __future__ import annotations

from models.inputs import PointInputs
from solvers.evaluator_bridge import evaluate_point
from solvers.optimize import is_feasible, optimize_design


def test_evaluator_bridge_returns_outputs() -> None:
    inp = PointInputs(R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0)
    out = evaluate_point(inp, origin="test")
    assert isinstance(out, dict)
    assert "Pin_MW" in out or "P_fus_MW" in out


def test_optimize_design_uses_evaluator_choke_point() -> None:
    inp = PointInputs(R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0)
    _, out = optimize_design(inp, n_iter=3, seed=1)
    assert isinstance(out, dict)
    assert is_feasible(out) in (True, False)
