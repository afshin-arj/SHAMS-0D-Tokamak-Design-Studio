from __future__ import annotations

from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from solvers.constraint_solver import solve_for_targets

def test_solve_report_is_attached():
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    targets = {"H98": 1.0, "Q_DT_eqv": 5.0}
    variables = {"Ip_MA": (inp.Ip_MA, max(0.1, 0.5*inp.Ip_MA), 1.5*inp.Ip_MA), "fG": (0.8, 0.1, 1.2)}
    res = solve_for_targets(inp, targets, variables, max_iter=2)
    assert hasattr(res, "report")
    assert isinstance(res.report, dict) or res.report is None
