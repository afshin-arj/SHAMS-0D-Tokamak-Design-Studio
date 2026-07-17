from __future__ import annotations

import importlib
from pathlib import Path


_CERT_MODULES = [
    "availability_reliability_certification_v391",
    "control_actuation_certification_v378",
    "cost_authority_certification_v388",
    "current_drive_certification_v381",
    "current_drive_library_certification_v395",
    "disruption_quench_certification_v377",
    "impurity_radiation_detachment_certification_v380",
    "materials_lifetime_certification_v384",
    "neutronics_activation_certification_v390",
    "neutronics_shield_attenuation_certification_v392",
    "plant_economics_certification_v383",
    "robust_envelope_v352",
    "stability_control_certification_v374",
    "structural_stress_certification_v389",
    "transport_confinement_certification_v376",
    "transport_profile_certification_v382",
]


def test_certification_modules_import() -> None:
    for name in _CERT_MODULES:
        mod = importlib.import_module(f"certification.{name}")
        assert mod is not None


def test_constraint_pipeline_mirror_v396_in_ledger() -> None:
    from constraints.system import build_constraints_from_outputs

    out = {
        "transport_spread_ratio_v396": 2.0,
        "transport_spread_max_v396": 1.5,
    }
    names = [c.name for c in build_constraints_from_outputs(out)]
    assert "Transport spread" in names


def test_constraint_pipeline_mirror_v407_in_governance() -> None:
    from constraints.constraints import evaluate_constraints

    out = {
        "tf_case_fluence_n_m2_per_fpy_v407": 1.0e20,
        "tf_case_fluence_max_n_m2_per_fpy_v392": 5.0e19,
    }
    names = [c.name for c in evaluate_constraints(out)]
    assert "TF case fluence" in names


def test_constraint_pipeline_mirror_v403_granular_in_governance() -> None:
    from constraints.constraints import evaluate_constraints

    out = {
        "dpa_fw_v403": 12.0,
        "dpa_fw_max_v403": 10.0,
        "tbr_proxy_v403": 0.8,
        "tbr_proxy_min_v403": 1.0,
    }
    names = [c.name for c in evaluate_constraints(out)]
    assert "FW DPA" in names
    assert "TBR proxy" in names


def test_constraint_pipeline_mirror_v398_in_ledger() -> None:
    from constraints.system import build_constraints_from_outputs

    out = {
        "vs_budget_margin_v398": 0.15,
        "vs_budget_margin_min_v398": 0.10,
        "rwm_proximity_index_v398": 0.4,
        "rwm_proximity_index_max_v398": 0.5,
    }
    names = [c.name for c in build_constraints_from_outputs(out)]
    assert "VS budget margin" in names
    assert "RWM proximity" in names


def test_constraint_pipeline_mirror_v397_q0_in_ledger() -> None:
    from constraints.system import build_constraints_from_outputs

    out = {
        "q0_proxy_v397": 1.05,
        "q0_proxy_min_v397": 1.0,
        "bootstrap_localization_index_v397": 0.8,
        "bootstrap_localization_max_v397": 1.0,
    }
    names = [c.name for c in build_constraints_from_outputs(out)]
    assert "q0 proxy" in names
    assert "Bootstrap localization" in names


def test_constraint_pipeline_mirror_v399_in_ledger() -> None:
    from constraints.system import build_constraints_from_outputs

    out = {
        "include_impurity_v399": 1.0,
        "impurity_v399_zeff": 2.5,
        "zeff_max_v399": 2.0,
        "Pin_MW": 100.0,
        "impurity_v399_prad_core_MW": 30.0,
        "prad_core_frac_max_v399": 0.25,
        "detachment_margin_v399": 0.1,
        "detachment_margin_min_v399": 0.0,
    }
    names = [c.name for c in build_constraints_from_outputs(out)]
    assert "Zeff" in names
    assert "Prad core fraction" in names
    assert "Detachment margin" in names


def test_detachment_index_not_duplicated_in_ledger() -> None:
    from constraints.system import build_constraints_from_outputs

    out = {"detachment_index": 1.0, "detachment_index_max": 2.0}
    names = [c.name for c in build_constraints_from_outputs(out)]
    assert names.count("Detachment access index") == 1
