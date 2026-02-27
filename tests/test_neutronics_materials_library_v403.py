from __future__ import annotations

import math

from src.analysis.neutronics_materials_library_v403 import evaluate_neutronics_materials_library_v403
from src.models.inputs import PointInputs


def test_v403_stack_parses_and_outputs_metrics() -> None:
    out = {
        "neutron_wall_load_MW_m2": 2.0,
        "availability_cert_v391": 0.75,
    }
    inp = PointInputs(
        R0_m=6.2,
        a_m=2.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=12.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=50.0,
        include_neutronics_materials_library_v403=True,
        nm_stack_json_v403=(
            "["
            "{\"material\":\"W\",\"thickness_m\":0.01,\"density_factor\":1.0},"
            "{\"material\":\"SS316\",\"thickness_m\":0.10,\"density_factor\":1.0},"
            "{\"material\":\"LiPb\",\"thickness_m\":0.40,\"density_factor\":1.0}"
            "]"
        ),
    )

    r = evaluate_neutronics_materials_library_v403(out, inp)
    assert r["include_neutronics_materials_library_v403"] is True
    assert "nm_attenuation_factor_v403" in r
    assert "dpa_fw_v403" in r and math.isfinite(r["dpa_fw_v403"])
    assert "he_appm_fw_v403" in r and math.isfinite(r["he_appm_fw_v403"])
    assert "tbr_proxy_v403" in r and math.isfinite(r["tbr_proxy_v403"])


def test_v403_margin_goes_negative_when_cap_too_low() -> None:
    out = {
        "neutron_wall_load_MW_m2": 3.0,
        "availability_cert_v391": 0.90,
    }
    inp = PointInputs(
        R0_m=6.2,
        a_m=2.0,
        kappa=1.8,
        Bt_T=5.0,
        Ip_MA=12.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=50.0,
        include_neutronics_materials_library_v403=True,
        nm_stack_json_v403='[{"material":"SS316","thickness_m":0.02,"density_factor":1.0}]',
        dpa_fw_max_v403=0.1,
    )

    r = evaluate_neutronics_materials_library_v403(out, inp)
    mm = float(r.get("nm_min_margin_frac_v403", float("nan")))
    assert math.isfinite(mm)
    assert mm < 0.0
