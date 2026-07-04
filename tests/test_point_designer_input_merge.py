"""Regression: Point Designer must merge preset knobs without duplicate-kwarg errors."""
from __future__ import annotations

from ui.point_inputs_factory import make_point_inputs, make_point_inputs_from, strip_point_input_knob_dupes


def _base_kwargs() -> dict:
    return dict(
        R0_m=1.85,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=8.0,
        Ti_keV=15.0,
        fG=0.8,
        Paux_MW=20.0,
    )


def test_make_point_inputs_merges_extras_and_explicit():
    extras = {"include_control_stability_authority_v398": True, "R0_m": 9.0}
    pi = make_point_inputs_from(extras, **_base_kwargs(), include_control_stability_authority_v398=False)
    assert pi.R0_m == 1.85
    assert pi.include_control_stability_authority_v398 is False


def test_make_point_inputs_positional_extras():
    extras = {"include_control_stability_authority_v398": True}
    pi = make_point_inputs(extras, **_base_kwargs(), include_control_stability_authority_v398=False)
    assert pi.include_control_stability_authority_v398 is False


def test_strip_point_input_knob_dupes():
    knobs = {
        "include_control_stability_authority_v398": True,
        "Paux_MW": 5.0,
        "zeff": 2.0,
    }
    out = strip_point_input_knob_dupes(knobs, "Paux_MW")
    assert "include_control_stability_authority_v398" not in out
    assert "Paux_MW" not in out
    assert out["zeff"] == 2.0
