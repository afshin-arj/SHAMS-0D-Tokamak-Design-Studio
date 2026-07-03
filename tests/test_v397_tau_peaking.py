from __future__ import annotations

from analysis.profile_proxy_v397 import evaluate_profile_proxy_v397
from models.inputs import PointInputs


def test_v397_tau_e_peaking_factor_emitted() -> None:
    inp = PointInputs(
        R0_m=1.85,
        a_m=0.6,
        kappa=1.75,
        Bt_T=12.0,
        Ip_MA=8.0,
        Ti_keV=10.0,
        fG=0.85,
        Paux_MW=25.0,
        include_profile_proxy_v397=True,
        profile_alpha_n_v397=2.0,
        profile_beta_n_v397=1.0,
    )
    patch = evaluate_profile_proxy_v397(inp, {"q95": 3.5})
    assert patch.get("profile_proxy_v397_enabled") is True
    fac = float(patch.get("tau_e_profile_factor_v397", float("nan")))
    assert fac == fac
    assert 0.0 < fac < 1.0
