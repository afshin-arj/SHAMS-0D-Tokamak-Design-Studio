"""Regression tests for Tier-1 audit fixes.

These tests pin four correctness fixes in the core 0-D evaluator
(`physics.hot_ion.hot_ion_point`) and its constraint builder:

1. DT neutron wall load must be non-zero and must be driven by the *total*
   fusion neutron power (DT + DD), not the DD branch alone.
2. The v397 1.5D Profile Proxy governance overlay must actually execute when
   enabled (it previously died with UnboundLocalError because `q95` was used
   before assignment, and the error was silently swallowed).
3. The von Mises / hoop stress duplication: `sigma_vm_MPa` is, under the current
   uniaxial thin-shell model, identical to `sigma_hoop_MPa`; there must not be a
   second, false-confidence "Von Mises stress" constraint against the same limit.
4. `radiation_model` dispatch: 'impurity_mix'/'lz_table' must activate the
   impurity physics path (matching the docs and UI), and an unknown value must
   raise rather than silently fall back to the fractional model.
"""
import math

import pytest

from dataclasses import replace

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs


def _dt_base(**overrides):
    """A representative compact, high-field DT operating point (SPARC-like)."""
    kw = dict(
        R0_m=1.85,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=8.7,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=25.0,
        fuel_mode="DT",
    )
    kw.update(overrides)
    return PointInputs(**kw)


def test_dt_neutron_wall_load_is_nonzero():
    """Bug 1: in DT mode the neutron wall-load proxy must not be ~0.

    Before the fix, S_n_W_m2 used only the DD branch (0.5 * Pfus_DD_W), which is
    ~0 for a DT plasma, so the proxy under-reported the wall load by ~10^3x.
    """
    out = hot_ion_point(_dt_base())

    pfus = float(out["Pfus_total_MW"])
    assert pfus > 100.0, "sanity: representative DT point should produce >100 MW fusion"

    # Neutron wall-load proxy (W/m^2) must be substantial, not residual DD noise.
    s_n_w_m2 = float(out["S_n_W_m2"])
    assert math.isfinite(s_n_w_m2)
    # 80% of ~1 GW fusion over an O(10) m^2 first wall is many MW/m^2 -> >1e6 W/m^2.
    assert s_n_w_m2 > 1.0e6, f"DT neutron wall load proxy too low: {s_n_w_m2:.3e} W/m^2"


def test_dt_neutron_wall_load_tracks_total_fusion_power():
    """Bug 1: the S_n proxy must scale with total Pfus, consistent with the
    independent `neutron_wall_load_MW_m2` proxy (which uses 0.8 * Pfus)."""
    out = hot_ion_point(_dt_base())

    s_n_MW_m2 = float(out["S_n_W_m2"]) / 1.0e6
    nwl_MW_m2 = float(out["neutron_wall_load_MW_m2"])

    assert nwl_MW_m2 > 0.0
    # Both proxies derive from the same ~0.8*Pfus neutron power and the same
    # first-wall area, so they should agree to within a modest factor.
    ratio = s_n_MW_m2 / nwl_MW_m2
    assert 0.5 < ratio < 2.0, (
        f"S_n proxy ({s_n_MW_m2:.3f}) and neutron_wall_load "
        f"({nwl_MW_m2:.3f}) MW/m^2 disagree by ratio {ratio:.2f}"
    )


def test_profile_proxy_v397_executes_in_pipeline():
    """Bug 2: the v397 overlay must run (no UnboundLocalError) when enabled."""
    inp = _dt_base(
        include_profile_proxy_v397=True,
        profile_alpha_n_v397=1.0,
        profile_beta_n_v397=1.0,
        profile_alpha_T_v397=1.5,
        profile_beta_T_v397=1.0,
        profile_alpha_j_v397=1.5,
        profile_beta_j_v397=1.0,
        profile_shear_shape_v397=0.5,
    )
    out = hot_ion_point(inp)

    # The error key must be absent: the overlay previously stored
    # "UnboundLocalError: ... 'q95' ..." here on every single call.
    assert out.get("profile_proxy_v397_error") is None, out.get(
        "profile_proxy_v397_error"
    )
    # And the overlay should have actually populated its diagnostics.
    assert "profile_peaking_n_v397" in out
    assert math.isfinite(float(out["profile_peaking_n_v397"]))


# ---------------------------------------------------------------------------
# Bug 3: von Mises / hoop stress duplication
# ---------------------------------------------------------------------------


def test_von_mises_equals_hoop_under_current_model():
    """The von Mises proxy is, by current modeling assumption, the hoop stress.

    This documents the assumption explicitly so a future genuinely-distinct
    von Mises implementation will break this test on purpose.
    """
    from engineering.tf_coil import von_mises_stress_MPa
    from phase1_systems import hoop_stress_MPa

    Bpeak_T, R_inner_m, t_struct_m = 22.0, 1.2, 0.15
    vm = von_mises_stress_MPa(Bpeak_T, R_inner_m, t_struct_m)
    hoop = hoop_stress_MPa(Bpeak_T, R_inner_m, t_struct_m)
    assert math.isfinite(vm) and vm > 0.0
    assert vm == pytest.approx(hoop, rel=1e-12)


def test_no_duplicate_von_mises_constraint():
    """There must be exactly one TF membrane-stress constraint (the hoop one),
    not a second "Von Mises stress" constraint against the same allowable."""
    out = hot_ion_point(_dt_base())
    cs = build_constraints_from_outputs(out)
    names = [c.name for c in cs]
    assert "Von Mises stress" not in names, "false-confidence duplicate constraint present"
    # The hoop membrane-stress constraint should still be evaluated when the
    # stress output is finite.
    if math.isfinite(float(out.get("sigma_hoop_MPa", float("nan")))):
        assert "Hoop stress" in names
    # The sigma_vm_MPa output key is retained for downstream consumers (v404).
    assert "sigma_vm_MPa" in out


# ---------------------------------------------------------------------------
# Bug 4: radiation_model dispatch
# ---------------------------------------------------------------------------


def _rad_base(**overrides):
    kw = dict(
        include_radiation=True,
        impurity_species="Ne",
        impurity_frac=0.02,
        f_rad_core=0.2,
    )
    kw.update(overrides)
    return _dt_base(**kw)


def test_impurity_mix_alias_matches_physics_path():
    """'impurity_mix' and 'lz_table' must activate the same impurity physics
    path as 'physics' (they are documented aliases), not the fractional model."""
    out_phys = hot_ion_point(_rad_base(radiation_model="physics"))
    out_mix = hot_ion_point(_rad_base(radiation_model="impurity_mix"))
    out_lz = hot_ion_point(_rad_base(radiation_model="lz_table"))

    # Impurity path records an Lz database provenance id; fractional does not.
    assert out_phys.get("radiation_db_id_used")
    assert float(out_mix["Prad_core_MW"]) == pytest.approx(float(out_phys["Prad_core_MW"]), rel=1e-12)
    assert float(out_lz["Prad_core_MW"]) == pytest.approx(float(out_phys["Prad_core_MW"]), rel=1e-12)


def test_impurity_path_differs_from_fractional():
    """With seeded impurities, the physics path must differ from fractional."""
    out_frac = hot_ion_point(_rad_base(radiation_model="fractional"))
    out_phys = hot_ion_point(_rad_base(radiation_model="physics"))
    assert float(out_frac["Prad_core_MW"]) != pytest.approx(float(out_phys["Prad_core_MW"]), rel=1e-6)


def test_unknown_radiation_model_raises():
    """An unrecognized radiation_model must fail loudly, not silently fall back."""
    with pytest.raises(ValueError):
        hot_ion_point(_rad_base(radiation_model="totally_made_up"))


def test_unknown_radiation_model_ignored_when_radiation_disabled():
    """Determinism guard: the dispatch only runs when radiation is enabled, so a
    bogus model string with include_radiation=False must not raise."""
    out = hot_ion_point(_dt_base(include_radiation=False, radiation_model="totally_made_up"))
    assert math.isfinite(float(out["Prad_core_MW"]))
