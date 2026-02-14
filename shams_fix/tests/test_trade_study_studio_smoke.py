from __future__ import annotations


def test_trade_study_runner_smoke() -> None:
    from evaluator.core import Evaluator
    from models.inputs import PointInputs
    from trade_studies.spec import default_knob_sets
    from trade_studies.runner import run_trade_study
    from trade_studies.families import attach_families, family_summary

    ev = Evaluator(cache_enabled=False)
    base = PointInputs(R0_m=1.81, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=7.5, Ti_keV=12.0, fG=0.85, Paux_MW=25.0)
    ks = default_knob_sets()[0]
    rep = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=ks.bounds,
        objectives=["min_R0"],
        objective_senses={"min_R0": "min"},
        n_samples=20,
        seed=3,
        include_outputs=False,
    )
    assert isinstance(rep, dict)
    assert "records" in rep and "feasible" in rep and "pareto" in rep and "meta" in rep
    recs = rep["records"]
    assert isinstance(recs, list) and len(recs) == 20

    recs2 = attach_families(recs)
    summ = family_summary(recs2)
    assert isinstance(summ, dict) and "rows" in summ


def test_mirage_pathfinding_scan_smoke() -> None:
    from evaluator.core import Evaluator
    from models.inputs import PointInputs
    from trade_studies.pathfinding import default_pathfinding_levers, one_knob_path_scan

    ev = Evaluator(cache_enabled=False)
    base = PointInputs(R0_m=1.81, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=7.5, Ti_keV=12.0, fG=0.85, Paux_MW=25.0)
    levers = default_pathfinding_levers(base)
    knob, lo, hi = levers[0]
    rep = one_knob_path_scan(ev, base, knob, lo=lo, hi=hi, n=7)
    assert rep.get("schema") == "mirage_path_scan.v1"
    assert rep.get("knob") == knob
    rows = rep.get("rows")
    assert isinstance(rows, list) and len(rows) == 7
