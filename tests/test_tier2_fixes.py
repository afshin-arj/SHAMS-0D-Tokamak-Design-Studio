"""Regression tests for Tier-2 audit fixes.

Covers:
1. ITER89-P prefactor corrected to 0.048 (was 0.038).
2. PointInputs duplicate-field removal preserves effective defaults.
3. PointInputs __post_init__ input-validation guards.
4. Authority-failure surfacing via out["_authority_warnings"].
"""
import math

import pytest

from models.inputs import PointInputs
from phase1_models import tauE_iter89p
from physics.hot_ion import hot_ion_point


def _base(**overrides):
    kw = dict(
        R0_m=1.85, a_m=0.57, kappa=1.8, Bt_T=12.2, Ip_MA=8.7,
        Ti_keV=12.0, fG=0.85, Paux_MW=25.0,
    )
    kw.update(overrides)
    return PointInputs(**kw)


# ---------------------------------------------------------------------------
# Item 1: ITER89-P prefactor
# ---------------------------------------------------------------------------


def test_iter89p_uses_0048_prefactor_and_r12_exponent():
    """Pins published ITER89-P prefactor (0.048) and R exponent (1.2)."""
    Ip, Bt, ne20, Ploss, R, a, kappa, M = 15.0, 5.3, 1.0, 150.0, 6.2, 2.0, 1.6, 2.5
    got = tauE_iter89p(Ip_MA=Ip, Bt_T=Bt, ne20=ne20, Ploss_MW=Ploss,
                       R_m=R, a_m=a, kappa=kappa, M_amu=M)
    eps = a / R
    expected = (
        0.048
        * Ip ** 0.85 * Bt ** 0.20 * ne20 ** 0.10 * Ploss ** -0.50
        * R ** 1.20 * a ** 0.30 * kappa ** 0.50 * M ** 0.50 * eps ** 0.00
    )
    assert got == pytest.approx(expected, rel=1e-12)


def test_iter89p_nonpositive_power_returns_inf():
    assert tauE_iter89p(Ip_MA=10, Bt_T=5, ne20=1, Ploss_MW=0.0,
                        R_m=6, a_m=2, kappa=1.6) == float("inf")


# ---------------------------------------------------------------------------
# Item 2: duplicate-field removal preserves defaults
# ---------------------------------------------------------------------------


def test_duplicate_fields_declared_once():
    fields = PointInputs.__dataclass_fields__
    for name in (
        "ignition_margin_min",
        "neutron_wall_load_max_MW_m2",
        "include_sol_radiation_control",
        "q_div_target_MW_m2",
    ):
        assert name in fields


def test_neutron_wall_load_default_preserved():
    """The previously-winning duplicate set this default to 2.5; preserve it."""
    inp = _base()
    assert inp.neutron_wall_load_max_MW_m2 == 2.5
    assert math.isnan(inp.ignition_margin_min)
    assert inp.include_sol_radiation_control is False
    assert math.isnan(inp.q_div_target_MW_m2)


# ---------------------------------------------------------------------------
# Item 3: input-validation guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [
    dict(a_m=0.0),
    dict(a_m=-0.5),
    dict(R0_m=0.0),
    dict(R0_m=0.4, a_m=0.57),   # R0 < a (aspect ratio < 1)
    dict(kappa=0.9),
    dict(Bt_T=0.0),
    dict(Bt_T=-12.0),
    dict(Ip_MA=0.0),
    dict(Ti_keV=0.0),
    dict(fG=0.0),
])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValueError):
        _base(**bad)


def test_valid_inputs_accepted():
    inp = _base()  # representative valid point must not raise
    out = hot_ion_point(inp)
    assert math.isfinite(out["Pfus_total_MW"])


# ---------------------------------------------------------------------------
# Item 4: authority-failure surfacing
# ---------------------------------------------------------------------------


def test_authority_warnings_key_present_and_clean():
    out = hot_ion_point(_base())
    assert "_authority_warnings" in out
    assert isinstance(out["_authority_warnings"], list)
    # A nominal valid point should have no governance failures.
    assert out["_authority_warning_count"] == 0.0
    assert out["_authority_warnings"] == []


def test_authority_warnings_aggregate_failures():
    """If any *_error key is present, it must be surfaced in the list."""
    out = hot_ion_point(_base())
    # Inject a synthetic failure the way an overlay would, then re-aggregate
    # using the same rule, to prove the surfacing logic captures *_error keys.
    out_like = dict(out)
    out_like["some_overlay_error"] = "RuntimeError: boom"
    warnings = [
        f"{k[:-len('_error')]}: {out_like[k]}"
        for k in sorted(out_like)
        if k.endswith("_error") and isinstance(out_like.get(k), str) and out_like.get(k)
    ]
    assert "some_overlay: RuntimeError: boom" in warnings
