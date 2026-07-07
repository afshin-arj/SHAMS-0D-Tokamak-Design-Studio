"""Trade Study governance + objective coverage."""
from __future__ import annotations

from evaluator.core import Evaluator
from models.inputs import PointInputs
from optimization.objectives import list_objectives
from trade_studies.runner import run_trade_study
from trade_studies.spec import default_knob_sets


def test_trade_study_uses_intent_feasibility_fields() -> None:
    ev = Evaluator(cache_enabled=False)
    base = PointInputs(R0_m=1.81, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=7.5, Ti_keV=12.0, fG=0.85, Paux_MW=25.0)
    ks = default_knob_sets()[1]
    rep_r = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=ks.bounds,
        objectives=["min_R0"],
        objective_senses={"min_R0": "min"},
        n_samples=25,
        seed=5,
        design_intent="Power Reactor (net-electric)",
    )
    rep_x = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=ks.bounds,
        objectives=["min_R0"],
        objective_senses={"min_R0": "min"},
        n_samples=25,
        seed=5,
        design_intent="Experimental Device (research)",
    )
    assert rep_r["meta"]["feasibility_mode"] == "governance+intent"
    n_fr = len(rep_r.get("feasible") or [])
    n_fx = len(rep_x.get("feasible") or [])
    assert n_fx >= n_fr
    row = (rep_r.get("records") or [None])[0]
    assert row is not None
    assert "governance_feasible" in row
    assert "first_failure" in row


def test_expanded_objective_registry() -> None:
    reg = list_objectives()
    for name in ("max_Q", "max_H98", "min_q_div", "max_TBR", "min_sigma_vm"):
        assert name in reg


def test_v351_atlas_honest_all_infeasible() -> None:
    from ui_nicegui.lib.external_optimizer_helpers import build_v351_atlas
    from ui_nicegui.session import DesignSession

    class _S(DesignSession):
        pass

    s = _S()
    s.trade_last = {
        "records": [{"is_feasible": False, "min_R0": 1.0}, {"is_feasible": False, "min_R0": 2.0}],
        "meta": {"objectives": ["min_R0"], "objective_senses": {"min_R0": "min"}},
    }
    atlas = build_v351_atlas(s, objectives=["min_R0"], senses={"min_R0": "min"})
    assert atlas.get("all_infeasible") is True
    assert atlas.get("n_feasible") == 0
    assert atlas.get("n_pareto") == 0
