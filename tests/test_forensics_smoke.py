import math

from src.models.inputs import PointInputs
from src.analysis.forensics import local_sensitivity
from physics.hot_ion import hot_ion_point


def test_local_forensics_runs_and_is_deterministic() -> None:
    pi = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.3,
        Ip_MA=12.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=50.0,
    )
    ff1 = local_sensitivity(pi, design_intent="Research")
    ff2 = local_sensitivity(pi, design_intent="Research")
    assert ff1["schema_version"] == "forensics.v1"
    assert ff1 == ff2

    # New UX-facing derived products (must stay deterministic)
    assert isinstance(ff1.get("tornado"), dict)
    assert isinstance(ff1.get("notes"), list)
    assert isinstance(ff1.get("dominant_advice"), dict)
    # sanity: at least one sensitivity entry exists for some constraint/knob pair
    sens = ff1.get("sensitivities", {})
    assert isinstance(sens, dict)
    any_num = False
    for _, row in sens.items():
        if isinstance(row, dict):
            for _, v in row.items():
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    any_num = True
                    break
        if any_num:
            break
    assert any_num


def test_exhaust_keys_present_when_lambda_q_enabled() -> None:
    pi = PointInputs(
        R0_m=3.0,
        a_m=1.0,
        kappa=1.8,
        Bt_T=5.3,
        Ip_MA=12.0,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=50.0,
        use_lambda_q=True,
    )
    out = hot_ion_point(pi)
    for k in ["lambda_q_mm", "q_div_MW_m2", "div_regime", "q_midplane_MW_m2"]:
        assert k in out
