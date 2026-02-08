from __future__ import annotations

import math


def test_neutronics_materials_stack_outputs_exist() -> None:
    """Smoke test for materials/neutronics authority hardening outputs."""

    from src.models.inputs import PointInputs
    from src.physics.hot_ion import hot_ion_point

    inp = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.7,
        Bt_T=5.3,
        Ip_MA=10.0,
        Ti_keV=12.0,
        fG=0.8,
        Paux_MW=50.0,
        shield_material="B4C",
        blanket_material="FLiBe",
        fw_material="W",
        vv_material="VV_STEEL",
        tf_material="REBCO",
        t_blanket_m=0.5,
        t_vv_m=0.05,
        t_fw_m=0.02,
        t_tf_wind_m=0.10,
        t_tf_struct_m=0.15,
    )

    out = hot_ion_point(inp)

    # New hardening outputs
    for k in [
        "neutron_attenuation_factor",
        "P_nuc_total_MW",
        "P_nuc_TF_MW",
        "fw_lifetime_yr",
        "blanket_lifetime_yr",
        "hts_fluence_per_fpy_stack_n_m2",
        "hts_lifetime_stack_yr",
        "TBR_domain_ok",
        "TBR_domain_margin",
    ]:
        assert k in out

    # Domain tightening outputs
    assert "TBR_domain_ok" in out
    assert "TBR_domain_margin" in out
    assert out.get("neutronics_domain_enforce", 0.0) in (0.0, 0, False)
    att = float(out["neutron_attenuation_factor"])
    if math.isfinite(att):
        assert 0.0 <= att <= 1.0

    Pn = float(out["P_nuc_total_MW"])
    if math.isfinite(Pn):
        assert Pn >= 0.0
