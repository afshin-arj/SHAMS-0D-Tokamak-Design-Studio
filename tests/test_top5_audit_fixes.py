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
    assert "Transport spread (v396)" in names


def test_constraint_pipeline_mirror_v407_in_governance() -> None:
    from constraints.constraints import evaluate_constraints

    out = {
        "tf_case_fluence_n_m2_per_fpy_v407": 1.0e20,
        "tf_case_fluence_max_n_m2_per_fpy_v392": 5.0e19,
    }
    names = [c.name for c in evaluate_constraints(out)]
    assert "TF case fluence (v407)" in names
