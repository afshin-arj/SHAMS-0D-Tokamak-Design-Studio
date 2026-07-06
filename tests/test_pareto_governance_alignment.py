"""Pareto feasibility aligns with Point Designer governance + intent policy."""
from __future__ import annotations

from models.inputs import PointInputs
from solvers.evaluator_bridge import evaluate_point
from solvers.optimize import pareto_optimize
from solvers.pareto_feasibility import annotate_pareto_feasibility
from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints, design_intent_key
from ui_nicegui.lib.pd_parity_helpers import failed_hard_names
from ui_nicegui.lib.verdict_core import verdict_summary


def test_annotate_matches_intent_policy_research_tbr_ignored() -> None:
    base = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=50.0)
    out = evaluate_point(base, origin="test")
    ann = annotate_pareto_feasibility(out, "Research")
    failed = failed_hard_names(out)
    cls = classify_failed_constraints(
        [str(x) for x in failed],
        design_intent="Research",
    )
    assert ann["is_feasible"] == (len(cls["blocking"]) == 0)
    if "TBR" in failed or any("tbr" in str(f).lower() for f in failed):
        assert "TBR" in ann.get("ignored_failures", []) or "TBR" in cls.get("ignored", [])


def test_pareto_row_governance_fields_present() -> None:
    base = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=50.0)
    bounds = {"R0_m": (1.6, 2.0), "Ip_MA": (6.0, 10.0)}
    res = pareto_optimize(
        base,
        bounds=bounds,
        objectives={"R0_m": "min", "P_e_net_MW": "max"},
        n_samples=12,
        seed=3,
        intent_key="Reactor",
        parallel=False,
    )
    rows = res.get("all") or []
    assert rows
    for row in rows[:5]:
        assert "governance_feasible" in row
        assert "dominant_constraint" in row


def test_research_feasible_superset_of_reactor_on_same_sample() -> None:
    base = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=50.0)
    bounds = {"R0_m": (1.5, 2.2), "fG": (0.5, 1.0)}
    res_r = pareto_optimize(
        base, bounds=bounds, objectives={"R0_m": "min", "Q_DT_eqv": "max"},
        n_samples=25, seed=11, intent_key="Reactor", parallel=False,
    )
    res_x = pareto_optimize(
        base, bounds=bounds, objectives={"R0_m": "min", "Q_DT_eqv": "max"},
        n_samples=25, seed=11, intent_key="Research", parallel=False,
    )
    n_fr = sum(1 for r in res_r.get("all") or [] if r.get("is_feasible"))
    n_fx = sum(1 for r in res_x.get("all") or [] if r.get("is_feasible"))
    assert n_fx >= n_fr


def test_verdict_governance_feasible_recorded_on_rows() -> None:
    base = PointInputs(R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.0, Ti_keV=15.0, fG=0.8, Paux_MW=50.0)
    out = evaluate_point(base, origin="test")
    v = verdict_summary(out)
    ann = annotate_pareto_feasibility(out, "Reactor")
    assert ann["governance_feasible"] == bool(v.get("feasible"))
