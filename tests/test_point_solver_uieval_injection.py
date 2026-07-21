"""Point Designer nested solver must use evaluator_bridge / ui_evaluate choke point."""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_point_solver_uses_evaluator_bridge_not_hot_ion():
    from src.solvers import point_solver as ps

    src = Path(ps.__file__).read_text(encoding="utf-8")
    assert "hot_ion_point" not in src
    assert "evaluate_point" in src
    assert "_eval_outputs" in src


def test_solve_fG_routes_through_bridge(monkeypatch):
    from src.models.inputs import PointInputs
    from src.solvers import point_solver as ps

    calls = {"n": 0}

    def _fake_eval(inp, *, origin="solver", Paux_for_Q_MW=None, **kw):
        calls["n"] += 1
        return {"Q_DT_eqv": 5.0, "H98": 1.0, "fG": float(getattr(inp, "fG", 0.8))}

    monkeypatch.setattr(ps, "evaluate_point", _fake_eval)
    base = PointInputs(
        R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0
    )
    sol, out, ok = ps.solve_fG_for_QDTeqv(base, target_Q=5.0, fG_min=0.5, fG_max=1.2, tol=1e-3, Paux_for_Q_MW=None)
    assert ok is True
    assert calls["n"] >= 1
    assert isinstance(out, dict)


def test_pd_evaluation_sets_override_and_recertifies():
    from ui_nicegui.lib import pd_solver_helpers as h

    src = inspect.getsource(h.run_point_designer_evaluation)
    assert "set_evaluate_point_override(_ui_eval)" in src
    assert 'origin="NiceGUI:Point Designer"' in src
    # Re-certify after solver/envelope (not only when out empty).
    assert "solver_audit" in src
    assert "ui_evaluate(" in src


def test_optimize_nsga_uses_evaluator_bridge():
    src = Path("src/solvers/optimize.py").read_text(encoding="utf-8")
    assert "from solvers.point_solver import evaluate_point" not in src
    assert "from solvers.evaluator_bridge import evaluate_point" in src


def test_hero_h98_phys_kpi_always_on_infeasible():
    from ui_nicegui.lib.pd_hero_kpis import hero_kpi_cells

    out = {"Q_DT_eqv": 4.0, "H98": 1.05, "P_e_net_MW": 80.0, "Pfus_total_MW": 200.0}
    summary = {"feasible": False, "verdict": "INFEASIBLE", "q_label": "Q=4", "nt_label": "n·T=n/a"}
    cells = hero_kpi_cells(out, summary, design_intent="Power Reactor (net-electric)")
    by = {c.label: c for c in cells}
    assert by["H98(y,2)"].suppressed is True
    assert by["Performance"].suppressed is True
    assert by["P_net,e"].suppressed is True
    assert by["Pfus"].suppressed is True
