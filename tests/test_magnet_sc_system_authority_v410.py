"""Tests for magnet SC system authority v410 (TF/PF/CS depth beyond v400)."""
from __future__ import annotations

import math

from analysis.magnet_sc_system_authority_v410 import evaluate_magnet_sc_system_authority_v410


def test_v410_disabled_returns_off() -> None:
    class Inp:
        include_magnet_sc_system_authority_v410 = False

    r = evaluate_magnet_sc_system_authority_v410({}, Inp())
    # Empty patch when OFF — no golden / artifact key pollution
    assert r == {}
    assert "magnet_v410_system_margin" not in r


def test_v410_computes_tf_pf_cs_family_ledger() -> None:
    class Inp:
        include_magnet_sc_system_authority_v410 = True
        magnet_technology = "HTS_REBCO"
        cs_Bmax_T = 12.0
        fragile_margin_frac = 0.05
        magnet_system_margin_min_v410 = float("nan")
        tf_family_margin_min_v410 = float("nan")
        pf_family_margin_min_v410 = float("nan")
        cs_family_margin_min_v410 = float("nan")

    out = {
        "magnet_v400_enabled": True,
        "magnet_v400_margin": 0.12,
        "magnet_v400_b_margin": 0.10,
        "magnet_v400_j_margin": 0.20,
        "magnet_v400_stress_margin": 0.50,
        "magnet_v400_sc_oper_margin": 0.15,
        "magnet_v400_t_window_margin": 0.30,
        "B_peak_T": 18.0,
        "B_peak_allow_T": 23.0,
        "hts_margin": 1.3,
        "hts_margin_min": 1.1,
        "Tcoil_K": 20.0,
        "Tcoil_min_K": 10.0,
        "Tcoil_max_K": 30.0,
        "cs_flux_margin": 0.25,
        "pf_I_peak_MA": 20.0,
        "pf_I_peak_max_MA": 30.0,
        "pf_stress_proxy": 0.4,
        "pf_stress_max": 1.0,
        "quench_proxy_margin": 0.2,
        "quench_proxy_min": 0.0,
        "coil_heat_nuclear_MW": 1.0,
        "coil_heat_nuclear_max_MW": 3.0,
        "magnet_contract_sha256": "abc123",
        "fragile_margin_frac": 0.05,
    }

    r = evaluate_magnet_sc_system_authority_v410(out, Inp())
    assert r["magnet_v410_enabled"] is True
    assert r["magnet_v410_screening_tier"] == "proxy"
    assert r["magnet_v410_overlay_version"].startswith("v410")
    assert r["magnet_v410_authority_id"] == "magnet_sc_system_authority_v410"

    for key in (
        "magnet_v410_tf_margin",
        "magnet_v410_pf_margin",
        "magnet_v410_cs_margin",
        "magnet_v410_system_margin",
    ):
        v = float(r[key])
        assert v == v and math.isfinite(v)

    assert r["magnet_v410_dominant_family"] in {"TF", "PF", "CS"}
    assert r["magnet_v410_system_tier"] in {"comfortable", "near_limit", "deficit", "unknown"}
    assert "PROXY" not in r["magnet_v410_provenance"].upper() or "proxy" in r["magnet_v410_provenance"].lower()
    assert "PROCESS MFILE" in r["magnet_v410_provenance"] or "not PROCESS" in r["magnet_v410_provenance"]


def test_v410_deterministic() -> None:
    class Inp:
        include_magnet_sc_system_authority_v410 = True
        magnet_technology = "LTS_NB3SN"
        cs_Bmax_T = 13.0

    out = {
        "magnet_v400_margin": 0.05,
        "B_peak_T": 12.0,
        "B_peak_allow_T": 13.0,
        "hts_margin": 1.4,
        "hts_margin_min": 1.2,
        "Tcoil_K": 5.0,
        "Tcoil_min_K": 4.2,
        "Tcoil_max_K": 6.0,
        "cs_flux_margin": 0.1,
        "pf_I_peak_MA": 15.0,
        "pf_I_peak_max_MA": 20.0,
        "fragile_margin_frac": 0.05,
    }
    a = evaluate_magnet_sc_system_authority_v410(out, Inp())
    b = evaluate_magnet_sc_system_authority_v410(out, Inp())
    assert a["magnet_v410_system_margin"] == b["magnet_v410_system_margin"]
    assert a["magnet_v410_dominant_family"] == b["magnet_v410_dominant_family"]
    assert a["magnet_v410_tf_margin"] == b["magnet_v410_tf_margin"]
    assert a["magnet_v410_cs_margin"] == b["magnet_v410_cs_margin"]
    assert a["magnet_v410_pf_margin"] == b["magnet_v410_pf_margin"]


def test_v410_cs_b_margin_uses_contract_allowable() -> None:
    class Inp:
        include_magnet_sc_system_authority_v410 = True
        magnet_technology = "HTS"
        cs_Bmax_T = 20.0

    out = {
        "magnet_v400_margin": 0.2,
        "B_peak_allow_T": 23.0,
        "B_peak_T": 18.0,
        "hts_margin": 1.2,
        "hts_margin_min": 1.1,
        "cs_flux_margin": 0.5,
        "fragile_margin_frac": 0.05,
    }
    r = evaluate_magnet_sc_system_authority_v410(out, Inp())
    # (23/20 - 1) = 0.15
    assert abs(float(r["magnet_v410_cs_B_margin"]) - 0.15) < 1e-9


def test_v410_optional_cap_echoed() -> None:
    class Inp:
        include_magnet_sc_system_authority_v410 = True
        magnet_technology = "HTS"
        cs_Bmax_T = 12.0
        magnet_system_margin_min_v410 = 0.05
        tf_family_margin_min_v410 = 0.0
        pf_family_margin_min_v410 = float("nan")
        cs_family_margin_min_v410 = float("nan")

    out = {
        "magnet_v400_margin": 0.2,
        "B_peak_allow_T": 23.0,
        "cs_flux_margin": 0.2,
        "pf_I_peak_MA": 10.0,
        "pf_I_peak_max_MA": 20.0,
        "fragile_margin_frac": 0.05,
    }
    r = evaluate_magnet_sc_system_authority_v410(out, Inp())
    assert float(r["magnet_system_margin_min_v410"]) == 0.05
    assert float(r["tf_family_margin_min_v410"]) == 0.0


def test_v410_ui_summary_helper() -> None:
    from ui_nicegui.lib.pd_parity_helpers import magnet_v410_summary

    assert magnet_v410_summary({"magnet_v410_enabled": False}) is None
    s = magnet_v410_summary(
        {
            "magnet_v410_enabled": True,
            "magnet_v410_screening_tier": "proxy",
            "magnet_v410_system_margin": 0.1,
            "magnet_v410_system_tier": "comfortable",
            "magnet_v410_dominant_family": "CS",
            "magnet_v410_dominant_family_margin": 0.1,
            "magnet_v410_tf_margin": 0.2,
            "magnet_v410_pf_margin": 0.3,
            "magnet_v410_cs_margin": 0.1,
            "magnet_v410_tf_tier": "comfortable",
            "magnet_v410_pf_tier": "comfortable",
            "magnet_v410_cs_tier": "comfortable",
            "magnet_v410_tf_dominant": "tf_v400_combined",
            "magnet_v410_pf_dominant": "pf_I",
            "magnet_v410_cs_dominant": "cs_B",
            "magnet_v410_provenance": "proxy",
        }
    )
    assert s is not None
    assert s["dominant_family"] == "CS"
    assert s["screening_tier"] == "proxy"


def _base_inp(**kwargs):
    from src.schema.inputs import PointInputs
    from dataclasses import replace

    base = PointInputs(
        R0_m=1.85,
        a_m=0.6,
        kappa=1.75,
        Bt_T=12.0,
        Ip_MA=8.0,
        Ti_keV=10.0,
        fG=0.85,
        Paux_MW=25.0,
    )
    return replace(base, **kwargs) if kwargs else base


def test_v410_hot_ion_flag_off_no_keys() -> None:
    """Flag OFF must not stamp v410 system margin into evaluator outputs."""
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_magnet_sc_system_authority_v410=False)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("magnet_v410_enabled", False)) is False
    assert "magnet_v410_system_margin" not in out


def test_v410_hot_ion_flag_on_stamps_ledger() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_magnet_sc_system_authority_v410=True)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("magnet_v410_enabled")) is True
    m = float(out["magnet_v410_system_margin"])
    assert out.get("magnet_v410_screening_tier") == "proxy"
    assert out.get("magnet_v410_dominant_family") in {"TF", "PF", "CS", "unknown"}
    assert math.isfinite(m)
