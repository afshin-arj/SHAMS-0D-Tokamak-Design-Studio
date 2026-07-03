from __future__ import annotations

from analysis.transport_envelope_v396 import evaluate_transport_envelope_v396


class _Inp:
    include_transport_envelope_v396 = True
    Ip_MA = 8.0
    Bt_T = 5.3
    R0_m = 6.2
    a_m = 2.0
    kappa = 1.7
    M_amu = 2.5
    transport_spread_max_v396 = float("nan")
    include_tauE_user_scaling_v396 = False


def test_v396_hmode_adds_scalings() -> None:
    out_l = {"ne20": 1.0, "P_SOL_MW": 50.0, "LH_ok": 0.0, "plasma_regime": "L-mode"}
    patch_l = evaluate_transport_envelope_v396(inp=_Inp(), out_partial=out_l)
    out_h = {"ne20": 1.0, "P_SOL_MW": 50.0, "LH_ok": 1.0, "plasma_regime": "H-mode"}
    patch_h = evaluate_transport_envelope_v396(inp=_Inp(), out_partial=out_h)
    assert patch_h.get("transport_envelope_regime_v396") == "H-mode"
    scal_h = patch_h.get("tauE_scalings_v396") or {}
    assert "Mirnov H" in scal_h
    assert "Shimomura H" in scal_h
    scal_l = patch_l.get("tauE_scalings_v396") or {}
    assert "Mirnov H" not in scal_l
