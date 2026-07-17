"""Independence ticket 1.2 — plant KPI honesty watermark tests."""
from __future__ import annotations

from decision.kpis import format_kpi_value, headline_kpis, KPI
from diagnostics.plant_kpi_honesty import (
    SCHEMA,
    build_plant_kpi_honesty,
    format_plant_kpi,
    plant_kpi_banner_text,
)
from models.inputs import PointInputs
from models.reference_machines import REFERENCE_MACHINES
from shams_io.run_artifact import build_run_artifact


def _infeas_cons() -> list:
    return [
        {
            "name": "Transport spread",
            "value": 5.0,
            "limit": 1.5,
            "sense": "<=",
            "passed": False,
            "severity": "hard",
            "margin_frac": -2.0,
            "units": "",
            "group": "transport",
        }
    ]


def _feas_cons() -> list:
    return [
        {
            "name": "beta_N",
            "value": 1.0,
            "limit": 3.0,
            "sense": "<=",
            "passed": True,
            "severity": "hard",
            "margin_frac": 0.5,
            "units": "",
            "group": "plasma",
        }
    ]


def test_plant_kpi_honesty_blocks_claims_when_hard_infeasible() -> None:
    out = {
        "P_e_net_MW": 120.0,
        "COE_proxy_USD_per_MWh": 85.0,
        "LCOE_proxy_USD_per_MWh": 90.0,
    }
    honesty = build_plant_kpi_honesty(out, hard_feasible=False)
    assert honesty["schema"] == SCHEMA
    assert honesty["watermark"] == "HARD_INFEASIBLE"
    assert honesty["claim_allowed"] is False
    assert honesty["kpis"]["Pe_net_MW"]["raw"] == 120.0
    assert honesty["kpis"]["Pe_net_MW"]["display"] == "— (diagnostic)"
    assert honesty["kpis"]["COE_proxy_USD_per_MWh"]["display"] == "— (diagnostic)"
    assert honesty["kpis"]["LCOE_proxy_USD_per_MWh"]["display"] == "— (diagnostic)"
    assert "HARD-INFEASIBLE" in plant_kpi_banner_text(honesty)


def test_plant_kpi_honesty_allows_claims_when_hard_feasible() -> None:
    out = {
        "P_e_net_MW": 120.0,
        "COE_proxy_USD_per_MWh": 85.0,
        "LCOE_proxy_USD_per_MWh": 90.0,
    }
    honesty = build_plant_kpi_honesty(out, hard_feasible=True)
    assert honesty["watermark"] == "HARD_FEASIBLE"
    assert honesty["claim_allowed"] is True
    assert "MW" in honesty["kpis"]["Pe_net_MW"]["display"]
    assert honesty["kpis"]["COE_proxy_USD_per_MWh"]["claim_allowed"] is True
    assert plant_kpi_banner_text(honesty) == ""


def test_format_plant_kpi_helper() -> None:
    honesty = build_plant_kpi_honesty({"P_e_net_MW": 50.0}, hard_feasible=False)
    assert format_plant_kpi(honesty, "Pe_net_MW") == "— (diagnostic)"


def test_run_artifact_stamps_plant_kpi_honesty_infeasible() -> None:
    """Independence 1.2: hard-infeasible artifacts watermark Pe_net/COE."""
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={
            "P_e_net_MW": 200.0,
            "P_net_e_MW": 200.0,
            "COE_proxy_USD_per_MWh": 70.0,
            "LCOE_proxy_USD_per_MWh": 75.0,
            "Q": 1.0,
            "transport_spread_ratio_v396": 5.0,
            "transport_spread_max_v396": 1.5,
        },
        constraints=_infeas_cons(),
        meta={"label": "plant_kpi_infeas", "mode": "point"},
    )
    assert art["kpis"]["feasible_hard"] is False
    assert "plant_kpi_honesty" in art
    honesty = art["plant_kpi_honesty"]
    assert honesty["schema"] == SCHEMA
    assert honesty["claim_allowed"] is False
    assert honesty["watermark"] == "HARD_INFEASIBLE"
    assert art["kpis"]["plant_claim_allowed"] is False
    assert art["kpis"]["Pe_net_display"] == "— (diagnostic)"
    assert art["kpis"]["COE_display"] == "— (diagnostic)"
    # Raw outputs untouched (L0 / bookkeeping preserved).
    assert float(art["outputs"]["P_e_net_MW"]) == 200.0


def test_run_artifact_stamps_plant_kpi_honesty_feasible() -> None:
    inp = PointInputs.from_dict(next(iter(REFERENCE_MACHINES.values())))
    art = build_run_artifact(
        inputs=inp.to_dict(),
        outputs={
            "P_e_net_MW": 200.0,
            "P_net_e_MW": 200.0,
            "COE_proxy_USD_per_MWh": 70.0,
            "beta_N": 1.0,
            "Q": 5.0,
        },
        constraints=_feas_cons(),
        meta={"label": "plant_kpi_feas", "mode": "point"},
    )
    assert art["kpis"]["feasible_hard"] is True
    honesty = art["plant_kpi_honesty"]
    assert honesty["schema"] == SCHEMA
    assert honesty["claim_allowed"] is True
    assert honesty["watermark"] == "HARD_FEASIBLE"
    assert art["kpis"]["plant_claim_allowed"] is True
    assert "MW" in str(art["kpis"]["Pe_net_display"])


def test_headline_kpis_watermark_when_hard_infeasible() -> None:
    outs = {"P_net_e_MW": 100.0, "COE_proxy_USD_per_MWh": 80.0, "Q_DT_eqv": 2.0}
    rows = dict(headline_kpis(outs, hard_feasible=False))
    assert rows["P_net_e [MW]"] == "— (diagnostic)"
    assert rows["COE_proxy [$/MWh]"] == "— (diagnostic)"
    # Non-plant KPIs still format normally.
    assert rows["Q_DT_eqv"] == "2.000"
    kpi = KPI("P_net_e_MW", "P_net_e [MW]", "MW", "{:.1f}")
    assert format_kpi_value(kpi, outs, hard_feasible=True) == "100.0"
