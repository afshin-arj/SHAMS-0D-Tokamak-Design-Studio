"""Tests for plant Sankey-grade ledger authority v419 (Independence 2.3)."""
from __future__ import annotations

import math

from analysis.plant_sankey_ledger_authority_v419 import (
    evaluate_plant_sankey_ledger_authority_v419,
)


def test_v419_disabled_returns_empty() -> None:
    class Inp:
        include_plant_sankey_ledger_authority_v419 = False

    r = evaluate_plant_sankey_ledger_authority_v419({}, Inp())
    assert r == {}
    assert "plant_v419_Pe_net_MW" not in r


def test_v419_flow_ledger_and_conservation() -> None:
    class Inp:
        include_plant_sankey_ledger_authority_v419 = True
        Paux_MW = 25.0
        eta_aux_wallplug = 0.40
        eta_cd_wallplug = 0.33
        eta_tf_wallplug = 0.95
        P_balance_of_plant_MW = 20.0
        P_pumps_MW = 5.0
        P_cryo_20K_MW = 0.0
        cryo_COP = 0.02
        P_tritium_plant_MW = float("nan")
        plant_sankey_conservation_tol_MW_v419 = 1e-3
        plant_sankey_f_recirc_max_v419 = float("nan")
        plant_sankey_Pe_net_min_MW_v419 = float("nan")
        blanket_energy_mult = 1.0

    # Construct L0-like plant closure residues
    Pfus = 100.0
    Palpha = 20.0
    Pn = 80.0
    Paux = 25.0
    Prad = 15.0
    Psol = Paux + Palpha - Prad  # 30
    Pth = 100.0
    eta = 0.40
    Pe_gross = eta * Pth
    P_hcd = Paux / 0.40  # 62.5
    Precirc = P_hcd + 20.0 + 5.0  # HCD + BOP + pumps
    Pe_net = Pe_gross - Precirc

    out = {
        "Pfus_total_MW": Pfus,
        "Palpha_MW": Palpha,
        "P_n_MW": Pn,
        "Prad_core_MW": Prad,
        "P_SOL_MW": Psol,
        "Pth_total_MW": Pth,
        "P_e_gross_MW": Pe_gross,
        "P_recirc_MW": Precirc,
        "P_e_net_MW": Pe_net,
        "Qe": Pe_gross / Precirc,
        "P_cd_launch_MW": 0.0,
        "P_cryo_MW": 0.0,
        "P_tf_ohmic_MW": 0.0,
    }

    r = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    assert r["plant_v419_enabled"] is True
    assert r["plant_v419_screening_tier"] == "proxy"
    assert r["plant_v419_overlay_version"].startswith("v419")
    assert r["plant_v419_authority_id"] == "plant_sankey_ledger_authority_v419"
    assert r["plant_v419_requires_kpi_honesty_watermark"] is True
    assert r["plant_v419_kpi_honesty_schema"] == "plant_kpi_honesty.v1"
    assert isinstance(r["plant_v419_flow_ledger"], list)
    assert len(r["plant_v419_flow_table"]) >= 5
    assert r["plant_v419_conservation_ok"] is True
    assert "PROXY" in r["plant_v419_provenance"].upper() or "proxy" in r["plant_v419_provenance"]
    assert "not PROCESS MFILE" in r["plant_v419_provenance"] or "PROCESS MFILE" in r["plant_v419_provenance"]
    assert r["plant_v419_units"]["power"] == "MW"
    assert abs(float(r["plant_v419_Pe_net_MW"]) - Pe_net) < 1e-9
    assert abs(float(r["plant_v419_Pe_gross_MW"]) - Pe_gross) < 1e-9
    assert isinstance(r["plant_v419_sankey_kwargs"], dict)
    assert "node" in r["plant_v419_sankey_kwargs"]
    assert "link" in r["plant_v419_sankey_kwargs"]
    checks = r["plant_v419_conservation_checks"]
    assert isinstance(checks, list)
    electric = next(c for c in checks if c["name"] == "electric_identity")
    assert electric["ok"] is True


def test_v419_deterministic() -> None:
    class Inp:
        include_plant_sankey_ledger_authority_v419 = True
        Paux_MW = 10.0
        eta_aux_wallplug = 0.5
        P_balance_of_plant_MW = 10.0
        P_pumps_MW = 2.0

    out = {
        "Pfus_total_MW": 50.0,
        "Palpha_MW": 10.0,
        "P_n_MW": 40.0,
        "Prad_core_MW": 5.0,
        "P_SOL_MW": 15.0,
        "Pth_total_MW": 50.0,
        "P_e_gross_MW": 20.0,
        "P_recirc_MW": 32.0,  # 10/0.5 + 10 + 2
        "P_e_net_MW": -12.0,
        "P_cd_launch_MW": 0.0,
        "P_cryo_MW": 0.0,
    }
    a = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    b = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    assert a["plant_v419_Pe_net_MW"] == b["plant_v419_Pe_net_MW"]
    assert a["plant_v419_f_recirc"] == b["plant_v419_f_recirc"]
    assert a["plant_v419_conservation_ok"] == b["plant_v419_conservation_ok"]
    assert a["plant_v419_n_flows"] == b["plant_v419_n_flows"]


def test_v419_optional_cap_echoed() -> None:
    class Inp:
        include_plant_sankey_ledger_authority_v419 = True
        Paux_MW = 5.0
        plant_sankey_f_recirc_max_v419 = 0.5
        plant_sankey_Pe_net_min_MW_v419 = 10.0
        P_balance_of_plant_MW = 5.0
        P_pumps_MW = 1.0

    out = {
        "Pfus_total_MW": 200.0,
        "Palpha_MW": 40.0,
        "P_n_MW": 160.0,
        "Prad_core_MW": 10.0,
        "P_SOL_MW": 35.0,
        "Pth_total_MW": 200.0,
        "P_e_gross_MW": 80.0,
        "P_recirc_MW": 16.0,
        "P_e_net_MW": 64.0,
        "P_cd_launch_MW": 0.0,
        "P_cryo_MW": 0.0,
    }
    r = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    assert float(r["plant_sankey_f_recirc_max_v419"]) == 0.5
    assert float(r["plant_sankey_Pe_net_min_MW_v419"]) == 10.0


def test_v419_ui_summary_helper() -> None:
    from ui_nicegui.lib.pd_parity_helpers import plant_v419_summary

    assert plant_v419_summary({"plant_v419_enabled": False}) is None
    s = plant_v419_summary(
        {
            "plant_v419_enabled": True,
            "plant_v419_screening_tier": "proxy",
            "plant_v419_overlay_version": "v419.0.0",
            "plant_v419_system_tier": "comfortable",
            "plant_v419_dominant_aspect": "HCD",
            "plant_v419_Pe_net_MW": 12.0,
            "plant_v419_Pe_gross_MW": 40.0,
            "plant_v419_Precirc_MW": 28.0,
            "plant_v419_f_recirc": 0.7,
            "plant_v419_conservation_ok": True,
            "plant_v419_n_flows": 10,
            "plant_v419_provenance": "proxy",
            "plant_v419_narrative": "test",
            "plant_v419_flow_table": [],
            "plant_v419_requires_kpi_honesty_watermark": True,
        }
    )
    assert s is not None
    assert s["screening_tier"] == "proxy"
    assert s["conservation_ok"] is True
    assert s["requires_kpi_honesty_watermark"] is True


def _base_inp(**kwargs):
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


def test_v419_hot_ion_flag_off_no_keys() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_plant_sankey_ledger_authority_v419=False)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("plant_v419_enabled", False)) is False
    assert "plant_v419_Pe_net_MW" not in out
    assert "P_e_net_MW" in out


def test_v419_hot_ion_flag_on_stamps_ledger() -> None:
    from src.evaluator.core import Evaluator

    inp = _base_inp(include_plant_sankey_ledger_authority_v419=True)
    res = Evaluator().evaluate(inp)
    out = dict(res.out or {})
    assert bool(out.get("plant_v419_enabled")) is True
    assert out.get("plant_v419_screening_tier") == "proxy"
    assert isinstance(out.get("plant_v419_flow_table"), list)
    assert math.isfinite(float(out["plant_v419_Pe_gross_MW"]))
    assert math.isfinite(float(out["plant_v419_Pe_net_MW"]))
    assert out.get("plant_v419_requires_kpi_honesty_watermark") is True
    assert bool(out.get("plant_v419_conservation_ok")) is True


def test_v419_flag_off_preserves_l0_numerics_vs_on() -> None:
    from src.evaluator.core import Evaluator

    off = dict(
        Evaluator().evaluate(_base_inp(include_plant_sankey_ledger_authority_v419=False)).out or {}
    )
    on = dict(
        Evaluator().evaluate(_base_inp(include_plant_sankey_ledger_authority_v419=True)).out or {}
    )
    for key in (
        "P_e_net_MW",
        "P_e_gross_MW",
        "P_recirc_MW",
        "Q",
        "P_fus_MW",
        "B_peak_T",
        "Pfus_total_MW",
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


def test_v419_sankey_builder_prefers_overlay() -> None:
    from shams_io.sankey import build_power_balance_sankey

    class Inp:
        include_plant_sankey_ledger_authority_v419 = True
        Paux_MW = 10.0
        P_balance_of_plant_MW = 5.0
        P_pumps_MW = 1.0
        eta_aux_wallplug = 0.5

    out = {
        "Pfus_total_MW": 50.0,
        "Palpha_MW": 10.0,
        "P_n_MW": 40.0,
        "Prad_core_MW": 5.0,
        "P_SOL_MW": 15.0,
        "Pth_total_MW": 50.0,
        "P_e_gross_MW": 20.0,
        "P_recirc_MW": 26.0,
        "P_e_net_MW": -6.0,
        "P_cd_launch_MW": 0.0,
        "P_cryo_MW": 0.0,
    }
    patch = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    art = {"outputs": {**out, **patch}}
    sank = build_power_balance_sankey(art)
    assert sank["valuesuffix"] == " MW"
    assert "Gross electric" in sank["node"]["label"] or "Net electric" in sank["node"]["label"]
    assert len(sank["link"]["value"]) >= 1


def test_v419_plant_kpi_honesty_interplay() -> None:
    """Overlay stamps honesty requirement; watermark still gates Pe_net display."""
    from diagnostics.plant_kpi_honesty import build_plant_kpi_honesty, format_plant_kpi

    class Inp:
        include_plant_sankey_ledger_authority_v419 = True
        Paux_MW = 10.0
        P_balance_of_plant_MW = 5.0
        P_pumps_MW = 1.0
        eta_aux_wallplug = 0.5

    out = {
        "Pfus_total_MW": 50.0,
        "Palpha_MW": 10.0,
        "P_n_MW": 40.0,
        "Prad_core_MW": 5.0,
        "P_SOL_MW": 15.0,
        "Pth_total_MW": 50.0,
        "P_e_gross_MW": 20.0,
        "P_recirc_MW": 26.0,
        "P_e_net_MW": -6.0,
        "P_cd_launch_MW": 0.0,
        "P_cryo_MW": 0.0,
    }
    patch = evaluate_plant_sankey_ledger_authority_v419(out, Inp())
    merged = {**out, **patch}
    honesty = build_plant_kpi_honesty(merged, hard_feasible=False)
    disp = format_plant_kpi(honesty, "Pe_net_MW", fallback_raw=merged["P_e_net_MW"], units="MW")
    assert "diagnostic" in disp.lower() or "—" in disp
    assert patch["plant_v419_requires_kpi_honesty_watermark"] is True
