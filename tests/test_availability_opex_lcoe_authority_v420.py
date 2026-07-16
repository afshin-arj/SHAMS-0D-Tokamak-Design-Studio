"""Tests for availability → OPEX/LCOE coupling authority v420 (Independence 2.4)."""
from __future__ import annotations

import math

from analysis.availability_opex_lcoe_authority_v420 import (
    evaluate_availability_opex_lcoe_authority_v420,
)


class _Inp:
    """Minimal PointInputs-like object for unit tests."""

    include_availability_opex_lcoe_authority_v420 = True
    availability = 0.70
    fixed_charge_rate = 0.10
    electricity_price_USD_per_MWh = 60.0
    opex_fixed_MUSD_per_y = 10.0
    cryo_wallplug_multiplier = 250.0
    P_cryo_20K_MW = 0.0
    eta_cd_wallplug = 0.35
    tritium_processing_cost_USD_per_g = 0.05
    k_cost_maint = 15.0
    avail_opex_lcoe_consistency_tol_v420 = float("nan")
    availability_min_v420 = float("nan")
    lcoe_max_USD_per_MWh_v420 = float("nan")
    opex_max_MUSD_per_y_v420 = float("nan")


def _base_out() -> dict:
    return {
        "P_e_net_MW": 100.0,
        "P_recirc_MW": 50.0,
        "duty_factor": 1.0,
        "availability_v368": 0.75,
        "replacement_cost_MUSD_per_year_v368": 20.0,
        "CAPEX_component_proxy_MUSD": 5000.0,
        "neutron_wall_load_MW_m2": 1.0,
        "T_burn_kg_per_day": 0.5,
        "P_cd_MW": 0.0,
    }


def test_v420_disabled_returns_empty() -> None:
    class Off(_Inp):
        include_availability_opex_lcoe_authority_v420 = False

    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), Off())
    assert r == {}
    assert "avail_v420_LCOE_USD_per_MWh" not in r


def test_v420_availability_precedence_and_provenance() -> None:
    out = _base_out()
    r = evaluate_availability_opex_lcoe_authority_v420(out, _Inp())
    assert r["avail_v420_enabled"] is True
    assert r["avail_v420_availability_source"] == "availability_v368"
    assert abs(float(r["avail_v420_availability"]) - 0.75) < 1e-12

    # Drop v368 -> falls to v359
    out2 = dict(out)
    del out2["availability_v368"]
    out2["availability_v359"] = 0.65
    r2 = evaluate_availability_opex_lcoe_authority_v420(out2, _Inp())
    assert r2["avail_v420_availability_source"] == "availability_v359"

    # Drop all ledgers -> availability_model
    out3 = dict(out)
    del out3["availability_v368"]
    out3["availability_model"] = 0.60
    r3 = evaluate_availability_opex_lcoe_authority_v420(out3, _Inp())
    assert r3["avail_v420_availability_source"] == "availability_model"

    # Nothing stamped -> input fallback
    out4 = {"P_e_net_MW": 100.0, "P_recirc_MW": 50.0}
    r4 = evaluate_availability_opex_lcoe_authority_v420(out4, _Inp())
    assert r4["avail_v420_availability_source"] == "inp.availability"
    assert abs(float(r4["avail_v420_availability"]) - 0.70) < 1e-12


def test_v420_energy_opex_lcoe_coupled_on_same_hours_basis() -> None:
    out = _base_out()
    inp = _Inp()
    r = evaluate_availability_opex_lcoe_authority_v420(out, inp)

    A = 0.75
    hours = 8760.0 * A * 1.0
    assert abs(float(r["avail_v420_hours_per_year_h"]) - hours) < 1e-9

    E = 100.0 * hours
    assert abs(float(r["avail_v420_E_net_MWh_per_y"]) - E) < 1e-6

    # OPEX electricity term uses the SAME hours (the coupling this overlay fixes)
    opex_recirc = 60.0 * 50.0 * hours / 1e6
    assert abs(float(r["avail_v420_OPEX_electric_recirc_MUSD_per_y"]) - opex_recirc) < 1e-9

    # Tritium term availability-coupled: g/day × 365 × A × duty × USD/g
    opex_trit = 500.0 * 365.0 * A * 1.0 * 0.05 / 1e6
    assert abs(float(r["avail_v420_OPEX_tritium_MUSD_per_y"]) - opex_trit) < 1e-12

    # Maintenance proxy: k × NWL (no double availability scaling)
    assert abs(float(r["avail_v420_OPEX_maintenance_MUSD_per_y"]) - 15.0) < 1e-12

    # LCOE decomposition sums exactly
    lcoe = float(r["avail_v420_LCOE_USD_per_MWh"])
    parts = (
        float(r["avail_v420_LCOE_capex_USD_per_MWh"])
        + float(r["avail_v420_LCOE_replacement_USD_per_MWh"])
        + float(r["avail_v420_LCOE_opex_USD_per_MWh"])
    )
    assert math.isfinite(lcoe)
    assert abs(lcoe - parts) < 1e-9

    # Replacement + CAPEX provenance
    assert r["avail_v420_replacement_source"] == "replacement_cost_MUSD_per_year_v368"
    assert r["avail_v420_CAPEX_source"] == "CAPEX_component_proxy_MUSD"

    # Hand-checked LCOE: (0.1*5000 + 20 + OPEX_total)*1e6 / E
    opex_total = float(r["avail_v420_OPEX_total_MUSD_per_y"])
    expect = (0.10 * 5000.0 + 20.0 + opex_total) * 1e6 / E
    assert abs(lcoe - expect) < 1e-9


def test_v420_consistency_checks_and_labels() -> None:
    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    assert r["avail_v420_consistency_ok"] is True
    checks = r["avail_v420_consistency_checks"]
    names = {c["name"] for c in checks}
    assert {"energy_identity", "opex_component_sum", "lcoe_decomposition"} <= names
    for c in checks:
        assert "units" in c and "rel_tol" in c
    assert r["avail_v420_screening_tier"] == "proxy"
    prov = str(r["avail_v420_provenance"])
    assert "PROXY" in prov.upper()
    assert "PROCESS MFILE" in prov
    assert "Generomak" in prov
    assert r["avail_v420_requires_kpi_honesty_watermark"] is True
    assert r["avail_v420_kpi_honesty_schema"] == "plant_kpi_honesty.v1"
    assert r["avail_v420_units"]["lcoe"] == "USD/MWh"
    assert r["avail_v420_units"]["opex"] == "MUSD/y"


def test_v420_cross_ledger_checks_are_informational() -> None:
    out = _base_out()
    # Stamp a v368 energy on a DIFFERENT basis -> cross check present, informational
    out["net_electric_MWh_per_year_v368"] = 100.0 * 8760.0 * 0.75 * 0.9
    r = evaluate_availability_opex_lcoe_authority_v420(out, _Inp())
    cross = [
        c
        for c in r["avail_v420_consistency_checks"]
        if c["name"].startswith("cross_ledger_")
    ]
    assert cross, "expected cross-ledger comparison rows"
    assert all(c.get("informational") for c in cross)
    # Gate does not depend on informational cross checks
    assert r["avail_v420_consistency_ok"] is True


def test_v420_deterministic() -> None:
    a = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    b = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    for key in (
        "avail_v420_availability",
        "avail_v420_E_net_MWh_per_y",
        "avail_v420_OPEX_total_MUSD_per_y",
        "avail_v420_LCOE_USD_per_MWh",
        "avail_v420_consistency_ok",
        "avail_v420_dominant_opex_driver",
    ):
        assert a[key] == b[key]


def test_v420_optional_caps_echoed() -> None:
    class Capped(_Inp):
        availability_min_v420 = 0.6
        lcoe_max_USD_per_MWh_v420 = 150.0
        opex_max_MUSD_per_y_v420 = 400.0

    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), Capped())
    assert float(r["availability_min_v420"]) == 0.6
    assert float(r["lcoe_max_USD_per_MWh_v420"]) == 150.0
    assert float(r["opex_max_MUSD_per_y_v420"]) == 400.0


def test_v420_no_energy_means_nan_lcoe_not_fake_number() -> None:
    out = _base_out()
    out["P_e_net_MW"] = -25.0  # infeasible bookkeeping residue
    r = evaluate_availability_opex_lcoe_authority_v420(out, _Inp())
    assert math.isnan(float(r["avail_v420_LCOE_USD_per_MWh"]))
    assert r["avail_v420_system_tier"] == "deficit"


def test_v420_ui_summary_helper() -> None:
    from ui_nicegui.lib.pd_parity_helpers import avail_v420_summary

    assert avail_v420_summary({"avail_v420_enabled": False}) is None
    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    s = avail_v420_summary(r)
    assert s is not None
    assert s["availability_source"] == "availability_v368"
    assert s["requires_kpi_honesty_watermark"] is True
    assert s["consistency_ok"] is True
    assert isinstance(s["opex_breakdown_MUSD_per_y"], dict)


def test_v420_chain_rows_helper() -> None:
    from analysis.availability_opex_lcoe_authority_v420 import (
        availability_lcoe_chain_rows,
    )

    assert availability_lcoe_chain_rows({}) is None
    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    rows = availability_lcoe_chain_rows(r)
    assert rows is not None
    stages = [row["stage"] for row in rows]
    assert stages == ["Availability", "Operating hours", "Annual net energy", "OPEX", "LCOE"]
    for row in rows:
        assert "units" in row and "provenance" in row


def _base_point_inputs(**kwargs):
    from dataclasses import replace

    from src.schema.inputs import PointInputs

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


def test_v420_hot_ion_flag_off_no_keys() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_point_inputs(include_availability_opex_lcoe_authority_v420=False)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("avail_v420_enabled", False)) is False
    assert "avail_v420_LCOE_USD_per_MWh" not in out
    assert "P_e_net_MW" in out


def test_v420_hot_ion_flag_on_stamps_chain() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_point_inputs(include_availability_opex_lcoe_authority_v420=True)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("avail_v420_enabled")) is True
    assert out.get("avail_v420_screening_tier") == "proxy"
    assert math.isfinite(float(out["avail_v420_availability"]))
    assert 0.0 <= float(out["avail_v420_availability"]) <= 1.0
    assert str(out.get("avail_v420_availability_source"))
    assert math.isfinite(float(out["avail_v420_OPEX_total_MUSD_per_y"]))
    assert out.get("avail_v420_requires_kpi_honesty_watermark") is True
    assert bool(out.get("avail_v420_consistency_ok")) is True


def test_v420_flag_off_preserves_l0_numerics_vs_on() -> None:
    from src.evaluator.core import Evaluator

    off = dict(
        Evaluator()
        .evaluate(_base_point_inputs(include_availability_opex_lcoe_authority_v420=False))
        .out
        or {}
    )
    on = dict(
        Evaluator()
        .evaluate(_base_point_inputs(include_availability_opex_lcoe_authority_v420=True))
        .out
        or {}
    )
    for key in (
        "P_e_net_MW",
        "P_e_gross_MW",
        "P_recirc_MW",
        "Q",
        "P_fus_MW",
        "Pfus_total_MW",
        "availability_model",
        "annual_net_MWh",
        "B_peak_T",
    ):
        if key not in off:
            continue
        a, b = off[key], on[key]
        if isinstance(a, float) and isinstance(b, float):
            if math.isnan(a) and math.isnan(b):
                continue
            assert a == b, f"L0 drift on {key}: {a} vs {b}"
        else:
            assert a == b, f"L0 drift on {key}"


def test_v420_plant_kpi_honesty_interplay() -> None:
    """v420 LCOE participates in the honesty watermark: infeasible -> diagnostic."""
    from diagnostics.plant_kpi_honesty import build_plant_kpi_honesty

    r = evaluate_availability_opex_lcoe_authority_v420(_base_out(), _Inp())
    merged = {**_base_out(), **r}
    # Remove other LCOE keys so the v420 key is the alias source
    honesty = build_plant_kpi_honesty(merged, hard_feasible=False)
    cell = honesty["kpis"]["LCOE_proxy_USD_per_MWh"]
    assert cell["source_key"] == "avail_v420_LCOE_USD_per_MWh"
    assert cell["claim_allowed"] is False
    assert cell["display"] == "— (diagnostic)"

    honesty_ok = build_plant_kpi_honesty(merged, hard_feasible=True)
    cell_ok = honesty_ok["kpis"]["LCOE_proxy_USD_per_MWh"]
    assert cell_ok["claim_allowed"] is True
    assert "USD/MWh" in cell_ok["display"]


def test_v420_constraint_caps_registered() -> None:
    from src.constraints.data.authority_specs_codegen import REGISTRY_SPECS

    v420 = [s for s in REGISTRY_SPECS if s.get("authority") == "v420"]
    assert len(v420) == 3
    keys = {s["value_key"] for s in v420}
    assert keys == {
        "avail_v420_availability",
        "avail_v420_LCOE_USD_per_MWh",
        "avail_v420_OPEX_total_MUSD_per_y",
    }
    assert all(
        s.get("enabled_key") == "include_availability_opex_lcoe_authority_v420"
        for s in v420
    )
