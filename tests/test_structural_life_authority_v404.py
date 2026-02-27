from __future__ import annotations

import math
from types import SimpleNamespace

from src.analysis.structural_life_authority_v404 import evaluate_structural_life_authority_v404


def _finite(x: float) -> bool:
    return isinstance(x, (int, float)) and (x == x) and math.isfinite(float(x))


def test_v404_off_returns_off():
    out = {}
    inp = SimpleNamespace(include_structural_life_v404=False)
    res = evaluate_structural_life_authority_v404(out, inp)
    assert res.get("include_structural_life_v404") is False


def test_v404_basic_margins_monotonic_with_sigma():
    # Use VV component which has a defined sigma proxy via v389 key.
    base_out = {"vv_sigma_ext_MPa_v389": 100.0, "sigma_vm_MPa": 200.0}
    inp = SimpleNamespace(
        include_structural_life_v404=True,
        material_vv_v404="SS316",
        T_vv_K_v404=450.0,
        pulse_count_v404=1e5,
        hot_fraction_v404=0.2,
        service_years_v404=1.0,
        # disable buckling to isolate
        vv_t_m_v404=float("nan"),
        vv_R_m_v404=float("nan"),
    )
    r1 = evaluate_structural_life_authority_v404(dict(base_out), inp)
    assert r1.get("include_structural_life_v404") is True
    m1 = float(r1.get("struct_global_min_margin_v404", float("nan")))
    assert m1 == m1  # should be finite-ish for this proxy test

    # Increase stress -> margin should not improve
    out2 = dict(base_out)
    out2["vv_sigma_ext_MPa_v389"] = 200.0
    r2 = evaluate_structural_life_authority_v404(out2, inp)
    m2 = float(r2.get("struct_global_min_margin_v404", float("nan")))
    assert m2 <= m1 + 1e-9


def test_v404_buckling_improves_with_thickness():
    out = {"vv_sigma_ext_MPa_v389": 120.0}
    inp_thin = SimpleNamespace(
        include_structural_life_v404=True,
        material_vv_v404="SS316",
        T_vv_K_v404=450.0,
        pulse_count_v404=1e5,
        hot_fraction_v404=0.2,
        service_years_v404=1.0,
        vv_t_m_v404=0.02,
        vv_R_m_v404=2.0,
    )
    r_thin = evaluate_structural_life_authority_v404(out, inp_thin)
    tbl_thin = r_thin.get("struct_margin_table_v404", [])
    vv_row_thin = [r for r in tbl_thin if r.get("component") == "VV"][0]
    mb_thin = float(vv_row_thin.get("buckling_margin", float("nan")))

    inp_thick = SimpleNamespace(**{**inp_thin.__dict__, "vv_t_m_v404": 0.04})
    r_thick = evaluate_structural_life_authority_v404(out, inp_thick)
    tbl_thick = r_thick.get("struct_margin_table_v404", [])
    vv_row_thick = [r for r in tbl_thick if r.get("component") == "VV"][0]
    mb_thick = float(vv_row_thick.get("buckling_margin", float("nan")))

    assert _finite(mb_thin) and _finite(mb_thick)
    assert mb_thick > mb_thin
