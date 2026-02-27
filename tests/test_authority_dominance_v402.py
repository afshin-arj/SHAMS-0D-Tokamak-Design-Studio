from __future__ import annotations

import math

from src.models.inputs import PointInputs
from analysis.authority_dominance_v402 import evaluate_authority_dominance_v402


def test_v402_runs_and_ranks() -> None:
    inp = PointInputs(
        # minimal required base inputs
        R0_m=3.0,
        a_m=1.0,
        kappa=1.7,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=50.0,
        include_authority_dominance_v402=True,
        transport_spread_ref_v402=3.0,
        profile_peaking_p_ref_v402=3.0,
        zeff_ref_max_v402=2.5,
    )

    out = {
        # v396
        "transport_spread_ratio_v396": 4.0,
        "transport_spread_cap_enabled_v396": False,
        # v397
        "profile_peaking_p_v397": 2.5,
        # v398
        "vs_budget_margin_v398": 0.15,
        "vde_headroom_v398": 0.20,
        "rwm_proximity_index_v398": 0.30,
        # v399-ish
        "impurity_v399_zeff": 2.2,
        "detachment_margin": 0.10,
        # v400
        "magnet_v400_margin": 0.08,
        # v401
        "nm_min_margin_frac_v401": 0.12,
        "nm_contract_tier_v401": "NOMINAL",
        # global feasibility (for mirage flag)
        "is_feasible": True,
    }

    res = evaluate_authority_dominance_v402(out=out, inp=inp)
    assert res["include_authority_dominance_v402"] is True
    assert isinstance(res["dominance_order_v402"], list)
    assert len(res["dominance_order_v402"]) >= 3

    mm = float(res["global_min_margin_v402"])
    assert mm == mm and math.isfinite(mm)

    # Transport should likely be the worst here since spread>ref => negative margin.
    dom = str(res["global_dominant_authority_v402"])
    assert dom in {
        "TRANSPORT",
        "PROFILE",
        "CONTROL",
        "EXHAUST_RADIATION",
        "MAGNET",
        "NEUTRONICS_MATERIALS",
    }

    # Ensure stable keys exist
    assert "regime_class_v402" in res
    assert "mirage_flag_v402" in res
