from __future__ import annotations

from analysis.cd_mix_plant_ledger_v408 import evaluate_cd_mix_plant_ledger_v408
from analysis.elm_transient_heat_v409 import evaluate_elm_transient_heat_v409
from models.inputs import PointInputs


def test_elm_v409_overlay_disabled_by_default() -> None:
    inp = PointInputs(R0_m=1.85, a_m=0.6, kappa=1.75, Bt_T=12.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.85, Paux_MW=25.0)
    patch = evaluate_elm_transient_heat_v409({"q_parallel_MW_per_m2": 50.0, "W_th_MJ": 100.0}, inp)
    assert float(patch["include_elm_transient_heat_v409"]) == 0.0


def test_cd_mix_plant_ledger_v408() -> None:
    inp = PointInputs(
        R0_m=1.85,
        a_m=0.6,
        kappa=1.75,
        Bt_T=12.0,
        Ip_MA=8.0,
        Ti_keV=10.0,
        fG=0.85,
        Paux_MW=25.0,
        cd_mix_enable=True,
        cd_mix_frac_eccd=0.6,
        cd_mix_frac_lhcd=0.4,
    )
    out = {"P_cd_ECCD_MW": 10.0, "P_cd_LHCD_MW": 5.0, "eta_cd_wallplug_ECCD": 0.4, "eta_cd_wallplug_LHCD": 0.35}
    patch = evaluate_cd_mix_plant_ledger_v408(out, inp)
    assert float(patch["cd_mix_frac_sum"]) == 1.0
    assert float(patch["P_cd_eccd_el_MW"]) == 25.0
