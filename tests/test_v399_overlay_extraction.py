from __future__ import annotations

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point


def test_v399_overlay_keys_present_when_disabled() -> None:
    inp = PointInputs(R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0)
    out = hot_ion_point(inp)
    assert "include_impurity_v399" in out
    assert float(out["include_impurity_v399"]) == 0.0


def test_v399_error_key_on_bad_mix() -> None:
    inp = PointInputs(
        R0_m=1.85,
        a_m=0.6,
        kappa=1.75,
        Bt_T=12.0,
        Ip_MA=8.0,
        Ti_keV=10.0,
        fG=0.85,
        Paux_MW=25.0,
        include_impurity_v399=True,
        impurity_mix_json_v399="{not valid json",
    )
    out = hot_ion_point(inp)
    assert out.get("impurity_v399_error") or (
        isinstance(out.get("impurity_v399_validity"), dict) and "error" in out["impurity_v399_validity"]
    )
