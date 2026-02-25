from __future__ import annotations


def test_transport_envelope_v396_smoke() -> None:
    """v396: Transport Envelope 2.0 should be deterministic and import-safe."""

    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point

    inp = PointInputs(
        R0_m=6.2,
        a_m=2.0,
        kappa=1.8,
        Bt_T=6.0,
        Ip_MA=10.0,
        Ti_keV=12.0,
        fG=0.8,
        Paux_MW=50.0,
        include_transport_envelope_v396=True,
    )

    out1 = hot_ion_point(inp)
    out2 = hot_ion_point(inp)

    assert out1.get("transport_envelope_v396_enabled") is True
    for k in (
        "tauE_envelope_min_s_v396",
        "tauE_envelope_max_s_v396",
        "transport_spread_ratio_v396",
        "transport_credibility_tier_v396",
    ):
        assert k in out1
        assert out1[k] == out2[k]

    assert float(out1["tauE_envelope_min_s_v396"]) <= float(out1["tauE_envelope_max_s_v396"])
    assert float(out1["transport_spread_ratio_v396"]) >= 1.0
