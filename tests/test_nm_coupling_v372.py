from __future__ import annotations


def test_neutronics_materials_coupling_v372_smoke() -> None:
    """v372: neutronics–materials coupling should be deterministic and import-safe."""

    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints

    inp = PointInputs(
        R0_m=6.2,
        a_m=2.0,
        kappa=1.8,
        Bt_T=5.3,
        Ip_MA=12.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=50.0,
        include_neutronics_materials_coupling_v372=True,
        nm_material_class_v372="RAFM",
        nm_spectrum_class_v372="nominal",
        dpa_rate_eff_max_v372=30.0,
        damage_margin_min_v372=0.0,
    )

    out = hot_ion_point(inp)
    assert out.get("nm_coupling_v372_enabled") in (True, 1.0)
    assert "dpa_rate_eff_per_fpy_v372" in out
    assert "damage_margin_v372" in out

    # Constraints should include the explicit cap constraint when enabled
    cons = evaluate_constraints(out)
    assert cons is not None
    names = [getattr(c, "name", "") for c in cons]
    assert any("DPA_rate_eff_v372" in n for n in names)
