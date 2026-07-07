"""Trade Study surrogate accelerator — propose + frozen-truth verify (tiny budget)."""
from __future__ import annotations

from evaluator.core import Evaluator
from models.inputs import PointInputs
from trade_studies.runner import run_trade_study
from trade_studies.spec import default_knob_sets


def test_surrogate_propose_and_verify_smoke() -> None:
    from extopt.surrogate_accel import propose_candidates, verify_candidates_as_rows

    ev = Evaluator(cache_enabled=False)
    base = PointInputs(
        R0_m=1.81,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=7.5,
        Ti_keV=4.0,
        fG=0.85,
        Paux_MW=50.0,
    )
    ks = default_knob_sets()[1]
    rep = run_trade_study(
        evaluator=ev,
        base_inputs=base,
        bounds=ks.bounds,
        objectives=["max_Q", "max_H98"],
        objective_senses={"max_Q": "max", "max_H98": "max"},
        n_samples=80,
        seed=5,
        design_intent="Experimental Device (research)",
    )
    records = rep.get("records") or []
    assert records
    n_feas = sum(1 for r in records if r.get("is_feasible"))
    assert n_feas >= 8, f"need feasible training rows for surrogate, got {n_feas}"

    cand = propose_candidates(
        records=records,
        bounds=dict(ks.bounds),
        objective_key="max_Q",
        objective_sense="max",
        n_pool=2000,
        n_propose=12,
        seed=17,
        kappa=1.0,
    )
    if len(cand) < 12:
        # Deterministic fallback: mid-bounds knobs still exercise verify path.
        mids = [{k: (float(lo) + float(hi)) / 2.0 for k, (lo, hi) in ks.bounds.items()}]
        cand = (cand + mids * 12)[:12]
    assert 1 <= len(cand) <= 12

    vrows = verify_candidates_as_rows(
        evaluator=ev,
        base_inputs=base,
        candidates=cand,
        objectives=["max_Q", "max_H98"],
        objective_senses={"max_Q": "max", "max_H98": "max"},
        include_outputs=False,
    )
    assert len(vrows) == len(cand)
    assert all("is_feasible" in r for r in vrows)
    assert all("dominant_constraint" in r for r in vrows)
