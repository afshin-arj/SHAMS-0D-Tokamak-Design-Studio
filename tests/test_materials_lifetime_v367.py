from __future__ import annotations

import math


def test_materials_lifetime_v367_basic() -> None:
    from analysis.materials_lifetime_v367 import compute_materials_lifetime_closure_v367

    class _I:
        plant_design_lifetime_yr = 30.0
        fw_replace_interval_min_yr = float("nan")
        blanket_replace_interval_min_yr = float("nan")
        fw_capex_fraction_of_blanket = 0.2
        blanket_capex_fraction_of_blanket = 1.0
        replacement_installation_factor = 1.15

    out = {
        "fw_lifetime_yr": 5.0,
        "blanket_lifetime_yr": 6.0,
        "capex_blanket_shield_MUSD": 1000.0,
    }

    d = compute_materials_lifetime_closure_v367(out, _I())
    assert d["fw_replace_interval_y_v367"] == 5.0
    assert d["blanket_replace_interval_y_v367"] == 6.0
    # replacements over plant life: ceil(30/5)-1=5 ; ceil(30/6)-1=4
    assert d["fw_replacements_over_plant_life"] == 5
    assert d["blanket_replacements_over_plant_life"] == 4
    # annualized costs
    fw_cost = d["fw_replacement_cost_MUSD_per_year"]
    bl_cost = d["blanket_replacement_cost_MUSD_per_year"]
    assert math.isfinite(fw_cost) and fw_cost > 0
    assert math.isfinite(bl_cost) and bl_cost > 0


def test_materials_lifetime_v367_nan_safe() -> None:
    from analysis.materials_lifetime_v367 import compute_materials_lifetime_closure_v367

    class _I:
        plant_design_lifetime_yr = 30.0
        fw_replace_interval_min_yr = float("nan")
        blanket_replace_interval_min_yr = float("nan")
        fw_capex_fraction_of_blanket = 0.2
        blanket_capex_fraction_of_blanket = 1.0
        replacement_installation_factor = 1.15

    out = {}
    d = compute_materials_lifetime_closure_v367(out, _I())
    # Should not crash and should return schema keys.
    assert d.get("materials_lifetime_schema_version") == "v367.0"