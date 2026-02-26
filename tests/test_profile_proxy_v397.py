from __future__ import annotations

from dataclasses import replace


def test_profile_proxy_v397_disabled_returns_flag() -> None:
    from src.models.inputs import PointInputs
    from src.analysis.profile_proxy_v397 import evaluate_profile_proxy_v397

    inp = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=20.0,
    )
    out = evaluate_profile_proxy_v397(inp=inp, out_partial={"q95": 3.0})
    assert out.get("profile_proxy_v397_enabled") is False


def test_profile_proxy_v397_basic_monotonicity() -> None:
    """Peaking should increase when beta is increased (holding alpha fixed)."""
    from src.models.inputs import PointInputs
    from src.analysis.profile_proxy_v397 import evaluate_profile_proxy_v397

    base = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=10.0,
        Ti_keV=10.0,
        fG=0.8,
        Paux_MW=20.0,
        include_profile_proxy_v397=True,
        profile_alpha_n_v397=1.0,
        profile_beta_n_v397=1.0,
        profile_alpha_T_v397=1.5,
        profile_beta_T_v397=1.0,
        profile_alpha_j_v397=1.5,
        profile_beta_j_v397=1.0,
        profile_shear_shape_v397=0.5,
    )

    out1 = evaluate_profile_proxy_v397(inp=base, out_partial={"q95": 3.0})
    base2 = replace(base, profile_beta_n_v397=2.0)
    out2 = evaluate_profile_proxy_v397(inp=base2, out_partial={"q95": 3.0})

    assert out1.get("profile_proxy_v397_enabled") is True
    assert out2.get("profile_proxy_v397_enabled") is True
    assert float(out2["profile_peaking_n_v397"]) > float(out1["profile_peaking_n_v397"])
