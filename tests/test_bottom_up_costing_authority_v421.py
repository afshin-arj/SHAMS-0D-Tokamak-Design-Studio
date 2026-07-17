"""Tests for bottom-up modular costing authority v421 (Independence 2.5)."""
from __future__ import annotations

import math

from analysis.bottom_up_costing_authority_v421 import (
    DEFAULT_FRACTIONS,
    DEFAULT_UNIT_RATES,
    costing_account_rows,
    evaluate_bottom_up_costing_authority_v421,
)


class _Inp:
    """Minimal PointInputs-like object for unit tests."""

    include_bottom_up_costing_authority_v421 = True
    R0_m = 1.85
    a_m = 0.6
    kappa = 1.75
    Bt_T = 12.0
    Paux_MW = 25.0
    P_cryo_20K_MW = 0.2
    t_coil_proxy_m = 0.5
    t_shield_m = 0.7
    fixed_charge_rate = 0.10
    costing_consistency_tol_v421 = float("nan")
    capex_total_max_MUSD_v421 = float("nan")
    lcoe_bottom_up_max_USD_per_MWh_v421 = float("nan")


def _base_out() -> dict:
    return {
        "B_peak_T": 14.0,
        "q_div_MW_m2": 10.0,
        "Pth_total_MW": 500.0,
        "T_burn_kg_per_day": 0.5,
        "P_e_net_MW": 100.0,
    }


def test_v421_disabled_returns_empty() -> None:
    class Off(_Inp):
        include_bottom_up_costing_authority_v421 = False

    r = evaluate_bottom_up_costing_authority_v421(_base_out(), Off())
    assert r == {}
    assert "costing_v421_CAPEX_total_MUSD" not in r


def test_v421_account_structure_and_identities() -> None:
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    assert r["costing_v421_enabled"] is True

    ledger = r["costing_v421_account_ledger"]
    assert isinstance(ledger, list) and len(ledger) == 13
    accounts = {row["account"] for row in ledger}
    assert {
        "magnets",
        "blanket_first_wall",
        "divertor",
        "vacuum_vessel",
        "cryostat_cryoplant",
        "heating_current_drive",
        "tritium_plant_fuel_cycle",
        "power_conversion_bop",
        "buildings_site",
        "remote_handling",
        "instrumentation_control",
        "engineering_management",
        "contingency",
    } == accounts

    # Every account row is fully labeled (driver, units, rate, kind).
    for row in ledger:
        assert row["driver"], row
        assert row["driver_units"], row
        assert row["rate"], row
        assert row["kind"] in ("equipment", "direct_fraction", "indirect")
        assert float(row["cost_MUSD"]) >= 0.0

    # Bottom-up identities: direct = equipment + fractions; total = all rows.
    direct = float(r["costing_v421_direct_subtotal_MUSD"])
    indirect = float(r["costing_v421_indirect_subtotal_MUSD"])
    total = float(r["costing_v421_CAPEX_total_MUSD"])
    assert abs(total - (direct + indirect)) < 1e-9 * max(total, 1.0)
    assert abs(total - sum(float(row["cost_MUSD"]) for row in ledger)) < 1e-9 * max(total, 1.0)
    assert r["costing_v421_consistency_ok"] is True


def test_v421_hand_checked_accounts() -> None:
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())

    # cryoplant: 0.2 MW × 25 MUSD/MW = 5 MUSD
    assert abs(float(r["costing_v421_cryostat_cryoplant_MUSD"]) - 5.0) < 1e-12
    # heating/CD: 25 MW × 4 MUSD/MW = 100 MUSD
    assert abs(float(r["costing_v421_heating_current_drive_MUSD"]) - 100.0) < 1e-12
    # fuel cycle: 0.5 kg/day × 55 MUSD/(kg/day) = 27.5 MUSD
    assert abs(float(r["costing_v421_tritium_plant_fuel_cycle_MUSD"]) - 27.5) < 1e-12
    # BOP: 500 MWth × 0.45 = 225 MUSD
    assert abs(float(r["costing_v421_power_conversion_bop_MUSD"]) - 225.0) < 1e-12

    # magnets: area × t_coil × rho × USD/kg × MID field multiplier (B=14 T)
    area = 4.0 * math.pi**2 * 1.85 * 0.6 * 1.75
    magnet_expect = area * 0.5 * 7000.0 * 220.0 * 1.25 / 1e6
    assert abs(float(r["costing_v421_magnets_MUSD"]) - magnet_expect) < 1e-9 * magnet_expect
    assert "MID" in str(r["costing_v421_field_bin"])
    assert "geometry_proxy" in str(r["costing_v421_magnet_mass_source"])

    # divertor: blanket account × 0.12 (q_div=10 in mid band → mult 1.0)
    blanket = float(r["costing_v421_blanket_first_wall_MUSD"])
    assert abs(float(r["costing_v421_divertor_MUSD"]) - blanket * 0.12) < 1e-9 * blanket
    assert abs(float(r["costing_v421_qdiv_multiplier"]) - 1.0) < 1e-12

    # fraction accounts on equipment subtotal
    equip = float(r["costing_v421_equipment_subtotal_MUSD"])
    assert abs(float(r["costing_v421_buildings_site_MUSD"]) - equip * 0.20) < 1e-9 * equip
    assert abs(float(r["costing_v421_remote_handling_MUSD"]) - equip * 0.08) < 1e-9 * equip
    assert abs(float(r["costing_v421_instrumentation_control_MUSD"]) - equip * 0.05) < 1e-9 * equip

    # indirect: engineering 12% of direct; contingency 15% of (direct + eng)
    direct = float(r["costing_v421_direct_subtotal_MUSD"])
    eng = float(r["costing_v421_engineering_management_MUSD"])
    cont = float(r["costing_v421_contingency_MUSD"])
    assert abs(eng - direct * 0.12) < 1e-9 * direct
    assert abs(cont - (direct + eng) * 0.15) < 1e-9 * direct


def test_v421_prefers_v388_magnet_mass_when_stamped() -> None:
    out = _base_out()
    out["magnet_mass_proxy_v388_kg"] = 1.0e6
    r = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    assert r["costing_v421_magnet_mass_source"] == "magnet_mass_proxy_v388_kg"
    # 1e6 kg × 220 USD/kg × 1.25 / 1e6 = 275 MUSD
    assert abs(float(r["costing_v421_magnets_MUSD"]) - 275.0) < 1e-9


def test_v421_provenance_and_labels() -> None:
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    assert r["costing_v421_screening_tier"] == "proxy"
    prov = str(r["costing_v421_provenance"])
    assert "PROXY" in prov.upper()
    assert "Generomak" in prov
    assert "PROCESS MFILE" in prov
    assert r["costing_v421_requires_kpi_honesty_watermark"] is True
    assert r["costing_v421_kpi_honesty_schema"] == "plant_kpi_honesty.v1"
    assert r["costing_v421_units"]["capex"] == "MUSD"
    assert r["costing_v421_units"]["lcoe"] == "USD/MWh"
    # Transparent rate/fraction tables are echoed for reviewers.
    assert r["costing_v421_unit_rates"] == DEFAULT_UNIT_RATES
    assert r["costing_v421_fractions"] == DEFAULT_FRACTIONS


def test_v421_cross_ledger_checks_are_informational() -> None:
    out = _base_out()
    out["CAPEX_proxy_MUSD"] = 1234.0
    out["CAPEX_industrial_v388_MUSD"] = 4321.0
    r = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    cross = [
        c
        for c in r["costing_v421_consistency_checks"]
        if c["name"].startswith("cross_ledger_")
    ]
    assert len(cross) == 2
    assert all(c.get("informational") for c in cross)
    # Gate does not depend on informational cross checks
    assert r["costing_v421_consistency_ok"] is True


def test_v421_lcoe_requires_v420_chain() -> None:
    # Without the availability coupling overlay, no LCOE number is invented.
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    assert math.isnan(float(r["costing_v421_LCOE_USD_per_MWh"]))
    assert "enable availability" in str(r["costing_v421_LCOE_basis"]).lower()

    # With v420 stamped, LCOE restates on that same energy/OPEX basis.
    out = _base_out()
    out.update({
        "avail_v420_enabled": True,
        "avail_v420_E_net_MWh_per_y": 100.0 * 8760.0 * 0.75,
        "avail_v420_OPEX_total_MUSD_per_y": 50.0,
        "avail_v420_replacement_MUSD_per_y": 20.0,
        "avail_v420_fixed_charge_rate": 0.10,
    })
    r2 = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    capex = float(r2["costing_v421_CAPEX_total_MUSD"])
    expect = (0.10 * capex + 20.0 + 50.0) * 1e6 / (100.0 * 8760.0 * 0.75)
    lcoe = float(r2["costing_v421_LCOE_USD_per_MWh"])
    assert math.isfinite(lcoe)
    assert abs(lcoe - expect) < 1e-9 * expect


def test_v421_deterministic() -> None:
    a = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    b = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    for key in (
        "costing_v421_CAPEX_total_MUSD",
        "costing_v421_direct_subtotal_MUSD",
        "costing_v421_indirect_subtotal_MUSD",
        "costing_v421_dominant_account",
        "costing_v421_consistency_ok",
    ):
        assert a[key] == b[key]


def test_v421_optional_caps_echoed() -> None:
    class Capped(_Inp):
        capex_total_max_MUSD_v421 = 9000.0
        lcoe_bottom_up_max_USD_per_MWh_v421 = 200.0

    r = evaluate_bottom_up_costing_authority_v421(_base_out(), Capped())
    assert float(r["capex_total_max_MUSD_v421"]) == 9000.0
    assert float(r["lcoe_bottom_up_max_USD_per_MWh_v421"]) == 200.0


def test_v421_ui_account_rows_helper() -> None:
    assert costing_account_rows({}) is None
    assert costing_account_rows({"costing_v421_enabled": False}) is None
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    rows = costing_account_rows(r)
    assert rows is not None and len(rows) == 13
    for row in rows:
        assert "account" in row and "cost_MUSD" in row and "driver" in row


def test_v421_ui_summary_helper() -> None:
    from ui_nicegui.lib.pd_parity_helpers import costing_v421_summary

    assert costing_v421_summary({"costing_v421_enabled": False}) is None
    r = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    s = costing_v421_summary(r)
    assert s is not None
    assert s["requires_kpi_honesty_watermark"] is True
    assert s["consistency_ok"] is True
    assert isinstance(s["account_ledger"], list)
    # No version tag leaks into the label mapping.
    from ui_nicegui.lib.display_labels import authority_display

    assert authority_display("v421") == "Bottom-up modular costing"


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


def test_v421_hot_ion_flag_off_no_keys() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_point_inputs(include_bottom_up_costing_authority_v421=False)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("costing_v421_enabled", False)) is False
    assert "costing_v421_CAPEX_total_MUSD" not in out
    assert "P_e_net_MW" in out


def test_v421_hot_ion_flag_on_stamps_ledger() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_point_inputs(include_bottom_up_costing_authority_v421=True)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("costing_v421_enabled")) is True
    assert out.get("costing_v421_screening_tier") == "proxy"
    assert math.isfinite(float(out["costing_v421_CAPEX_total_MUSD"]))
    assert float(out["costing_v421_CAPEX_total_MUSD"]) > 0.0
    assert isinstance(out.get("costing_v421_account_ledger"), list)
    assert out.get("costing_v421_requires_kpi_honesty_watermark") is True
    assert bool(out.get("costing_v421_consistency_ok")) is True


def test_v421_flag_off_preserves_l0_numerics_vs_on() -> None:
    from src.evaluator.core import Evaluator

    off = dict(
        Evaluator()
        .evaluate(_base_point_inputs(include_bottom_up_costing_authority_v421=False))
        .out
        or {}
    )
    on = dict(
        Evaluator()
        .evaluate(_base_point_inputs(include_bottom_up_costing_authority_v421=True))
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
        "CAPEX_proxy_MUSD",
        "COE_proxy_USD_per_MWh",
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


def test_v421_plant_kpi_honesty_interplay() -> None:
    """v421 LCOE participates in the honesty watermark: infeasible -> diagnostic."""
    from diagnostics.plant_kpi_honesty import build_plant_kpi_honesty

    out = _base_out()
    out.update({
        "avail_v420_enabled": True,
        "avail_v420_E_net_MWh_per_y": 100.0 * 8760.0 * 0.75,
        "avail_v420_OPEX_total_MUSD_per_y": 50.0,
        "avail_v420_replacement_MUSD_per_y": 20.0,
        "avail_v420_fixed_charge_rate": 0.10,
    })
    r = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    merged = {**out, **r}
    honesty = build_plant_kpi_honesty(merged, hard_feasible=False)
    cell = honesty["kpis"]["LCOE_proxy_USD_per_MWh"]
    assert cell["source_key"] == "costing_v421_LCOE_USD_per_MWh"
    assert cell["claim_allowed"] is False
    assert cell["display"] == "— (diagnostic)"

    honesty_ok = build_plant_kpi_honesty(merged, hard_feasible=True)
    cell_ok = honesty_ok["kpis"]["LCOE_proxy_USD_per_MWh"]
    assert cell_ok["claim_allowed"] is True
    assert "USD/MWh" in cell_ok["display"]


def test_v421_ui_lcoe_display_uses_bottom_up_basis() -> None:
    """The costing panel LCOE must be the bottom-up restatement, never the
    global LCOE alias (which can sit on a different CAPEX basis)."""
    from ui_nicegui.lib.plant_kpi_honesty_ui import bottom_up_lcoe_display

    out = _base_out()
    out.update({
        "avail_v420_enabled": True,
        "avail_v420_E_net_MWh_per_y": 100.0 * 8760.0 * 0.75,
        "avail_v420_OPEX_total_MUSD_per_y": 50.0,
        "avail_v420_replacement_MUSD_per_y": 20.0,
        "avail_v420_fixed_charge_rate": 0.10,
        # A DIFFERENT finite LCOE on the v420 CAPEX basis — must NOT be shown
        # on the bottom-up costing panel.
        "avail_v420_LCOE_USD_per_MWh": 12.34,
    })
    r = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    merged = {**out, **r}
    lcoe_v421 = float(r["costing_v421_LCOE_USD_per_MWh"])
    assert math.isfinite(lcoe_v421)
    assert abs(lcoe_v421 - 12.34) > 1.0  # bases genuinely differ

    # The panel helper resolves feasibility from the constraint bundle here
    # (all pass) and must show the bottom-up number, never the v420 alias.
    disp_helper = bottom_up_lcoe_display(merged)
    assert f"{lcoe_v421:.3g}" in disp_helper
    assert "12.3" not in disp_helper

    # Hard-infeasible → watermark blocks the claim entirely.
    from diagnostics.plant_kpi_honesty import build_plant_kpi_honesty, format_plant_kpi

    honesty_bad = build_plant_kpi_honesty(merged, hard_feasible=False)
    disp_bad = format_plant_kpi(
        honesty_bad,
        "costing_v421_LCOE_USD_per_MWh",
        fallback_raw=merged.get("costing_v421_LCOE_USD_per_MWh"),
        units="USD/MWh",
    )
    assert disp_bad == "— (diagnostic)"

    honesty_ok = build_plant_kpi_honesty(merged, hard_feasible=True)
    disp = format_plant_kpi(
        honesty_ok,
        "costing_v421_LCOE_USD_per_MWh",
        fallback_raw=merged.get("costing_v421_LCOE_USD_per_MWh"),
        units="USD/MWh",
    )
    assert f"{lcoe_v421:.3g}" in disp
    assert "12.3" not in disp

    # Without the v420 chain, no LCOE number is invented on the panel either.
    r_solo = evaluate_bottom_up_costing_authority_v421(_base_out(), _Inp())
    merged_solo = {**_base_out(), **r_solo, "LCOE_proxy_USD_per_MWh": 99.0}
    honesty_solo = build_plant_kpi_honesty(merged_solo, hard_feasible=True)
    disp_solo = format_plant_kpi(
        honesty_solo,
        "costing_v421_LCOE_USD_per_MWh",
        fallback_raw=merged_solo.get("costing_v421_LCOE_USD_per_MWh"),
        units="USD/MWh",
    )
    assert disp_solo == "n/a"


def test_v421_nan_driver_flagged_in_ledger() -> None:
    out = _base_out()
    del out["Pth_total_MW"]
    out["Pth_total_MW"] = float("nan")
    r = evaluate_bottom_up_costing_authority_v421(out, _Inp())
    # NaN drivers land as 0-cost accounts but must be flagged, not silent.
    rows = {row["account"]: row for row in r["costing_v421_account_ledger"]}
    bop = rows["power_conversion_bop"]
    assert float(bop["cost_MUSD"]) == 0.0
    assert "driver not stamped" in str(bop["note"])


def test_v421_constraint_caps_registered() -> None:
    from src.constraints.data.authority_specs_codegen import REGISTRY_SPECS

    v421 = [s for s in REGISTRY_SPECS if s.get("authority") == "v421"]
    assert len(v421) == 2
    keys = {s["value_key"] for s in v421}
    assert keys == {
        "costing_v421_CAPEX_total_MUSD",
        "costing_v421_LCOE_USD_per_MWh",
    }
    assert all(
        s.get("enabled_key") == "include_bottom_up_costing_authority_v421"
        for s in v421
    )
    # UI display names must carry no version tag.
    for s in v421:
        assert "v421" not in str(s["name"]).lower()
        assert "v42" not in str(s["name"]).lower()
