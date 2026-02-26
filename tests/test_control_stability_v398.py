from __future__ import annotations

import math
from types import SimpleNamespace

from src.analysis.control_stability_v398 import evaluate_control_stability_v398


def test_v398_disabled_returns_flag():
    inp = SimpleNamespace(include_control_stability_authority_v398=False)
    out = evaluate_control_stability_v398(inp=inp, out_partial={})
    assert out.get("control_stability_v398_enabled") is False


def test_v398_vs_budget_margin_computation():
    inp = SimpleNamespace(include_control_stability_authority_v398=True, include_control_contracts=False)
    out = evaluate_control_stability_v398(
        inp=inp,
        out_partial={"cs_flux_required_Wb": 100.0, "cs_flux_available_Wb": 125.0, "cs_flux_margin": 0.25},
    )
    assert out["control_stability_v398_enabled"] is True
    assert math.isfinite(out["vs_budget_margin_v398"])
    assert abs(out["vs_budget_margin_v398"] - 0.25) < 1e-12


def test_v398_headroom_min_logic():
    inp = SimpleNamespace(include_control_stability_authority_v398=True, include_control_contracts=True)
    out = evaluate_control_stability_v398(
        inp=inp,
        out_partial={
            "cs_flux_required_Wb": 100.0,
            "cs_flux_available_Wb": 120.0,
            "vs_control_power_req_MW": 10.0,
            "vs_control_power_max_MW": 12.0,
            "vs_bandwidth_req_Hz": 100.0,
            "vs_bandwidth_max_Hz": 130.0,
        },
    )
    # power headroom = 0.2, bw headroom = 0.3 => min = 0.2
    assert abs(out["vde_headroom_v398"] - 0.2) < 1e-12
    assert out["vde_headroom_tier_v398"] in ("comfortable", "near_limit", "deficit", "unknown")


def test_v398_rwm_index_profile_penalties():
    inp = SimpleNamespace(include_control_stability_authority_v398=True, include_control_contracts=True)
    out = evaluate_control_stability_v398(
        inp=inp,
        out_partial={
            "rwm_chi": 1.0,  # base -> 1
            "q0_proxy_v397": 0.7,
            "profile_peaking_p_v397": 3.0,
            "bootstrap_localization_index_v397": 0.9,
            "li_proxy_v397": 2.0,
        },
    )
    assert 0.0 <= out["rwm_proximity_index_v398"] <= 1.0
    assert out["rwm_proximity_tier_v398"] in ("benign", "watch", "critical", "unknown")
