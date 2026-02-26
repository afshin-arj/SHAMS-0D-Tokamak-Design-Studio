from __future__ import annotations

import math


def test_v401_disabled_returns_off() -> None:
    from src.analysis.neutronics_materials_authority_v401 import evaluate_neutronics_materials_authority_v401

    class Inp:
        include_neutronics_materials_authority_v401 = False

    out = {}
    r = evaluate_neutronics_materials_authority_v401(out, Inp())
    assert r["include_neutronics_materials_authority_v401"] is False
    assert r["nm_fragility_class_v401"] == "OFF"
    assert isinstance(r["nm_contract_items_v401"], list)


def test_v401_feasible_nominal_example() -> None:
    from src.analysis.neutronics_materials_authority_v401 import evaluate_neutronics_materials_authority_v401

    class Inp:
        include_neutronics_materials_authority_v401 = True
        nm_contract_tier_v401 = "NOMINAL"
        nm_fragile_margin_frac_v401 = 0.10

    # Values comfortably within nominal defaults
    out = {
        "tf_case_fluence_n_m2_per_fpy_v392": 5.0e21,
        "bioshield_dose_rate_uSv_h_v392": 3.0,
        "P_nuc_TF_MW": 2.0,
        "dpa_per_fpy_v390": 8.0,
        "fw_He_total_appm": 2000.0,
        "activation_index_v390": 0.7,
        "TBR": 1.20,
    }

    r = evaluate_neutronics_materials_authority_v401(out, Inp())
    assert r["include_neutronics_materials_authority_v401"] is True
    assert r["nm_contract_tier_v401"] == "NOMINAL"
    assert r["nm_fragility_class_v401"] == "FEASIBLE"
    mm = float(r["nm_min_margin_frac_v401"])
    assert mm == mm and math.isfinite(mm)
    assert mm > 0.10
    assert isinstance(r["nm_contract_items_v401"], list)
    assert len(r["nm_contract_items_v401"]) >= 6


def test_v401_infeasible_when_over_limit() -> None:
    from src.analysis.neutronics_materials_authority_v401 import evaluate_neutronics_materials_authority_v401

    class Inp:
        include_neutronics_materials_authority_v401 = True
        nm_contract_tier_v401 = "ROBUST"
        nm_fragile_margin_frac_v401 = 0.10

    # Exceed robust TF-case fluence default
    out = {
        "tf_case_fluence_n_m2_per_fpy_v392": 2.0e22,
        "bioshield_dose_rate_uSv_h_v392": 1.0,
        "P_nuc_TF_MW": 1.0,
        "dpa_per_fpy_v390": 5.0,
        "fw_He_total_appm": 1500.0,
        "activation_index_v390": 0.5,
        "TBR": 1.15,
    }
    r = evaluate_neutronics_materials_authority_v401(out, Inp())
    assert r["nm_fragility_class_v401"] == "INFEASIBLE"
    assert r["nm_dominant_driver_v401"] in {"tf_case_fluence", "unknown"}
