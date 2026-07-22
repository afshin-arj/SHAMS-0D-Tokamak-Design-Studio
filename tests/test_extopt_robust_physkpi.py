"""ExtOpt Robust Pareto PHYS-KPI-001 honesty (FAIL claim FoMs)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_claim_key_strips_robust_prefix():
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        allow_infeasible_scatter_point,
        claim_key_for_objective_column,
        is_claim_scatter_axis,
    )

    assert claim_key_for_objective_column("robust_P_e_net_MW") == "P_e_net_MW"
    assert claim_key_for_objective_column("degrade_Q_DT_eqv") == "Q_DT_eqv"
    assert claim_key_for_objective_column("robust_R0_m") is None
    assert is_claim_scatter_axis("robust_H98")
    assert not allow_infeasible_scatter_point(x_key="robust_P_e_net_MW", y_key="robust_Q_DT_eqv")
    assert allow_infeasible_scatter_point(x_key="R0_m", y_key="Bt_T")


def test_watermark_robust_pareto_rows():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_robust_pareto_rows

    rows = [
        {
            "i": 0,
            "tier": "FAIL",
            "nominal_feasible": False,
            "robust_P_e_net_MW": 120.0,
            "degrade_Q_DT_eqv": -0.2,
            "robust_R0_m": 6.2,
            "env_worst_margin": -0.1,
        },
        {
            "i": 1,
            "tier": "ROBUST",
            "nominal_feasible": True,
            "robust_P_e_net_MW": 40.0,
            "degrade_Q_DT_eqv": -0.05,
            "robust_R0_m": 5.5,
        },
    ]
    disp = watermark_robust_pareto_rows(rows)
    assert "diagnostic" in str(disp[0]["robust_P_e_net_MW"]).lower()
    assert "diagnostic" in str(disp[0]["degrade_Q_DT_eqv"]).lower()
    assert disp[0]["robust_R0_m"] == 6.2
    assert "diagnostic" not in str(disp[1]["robust_P_e_net_MW"]).lower()
    assert disp[1]["robust_P_e_net_MW"] == 40.0


def test_watermark_robust_pareto_export():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_robust_pareto_export

    art = {
        "schema": "robust_pareto.v1",
        "rows": [
            {
                "i": 0,
                "tier": "FAIL",
                "nominal_feasible": False,
                "robust_Q_DT_eqv": 15.0,
            }
        ],
        "points": [
            {
                "index": 0,
                "nominal_outputs": {"Q_DT_eqv": 15.0, "R0_m": 6.0, "H98": 1.2},
            }
        ],
    }
    out = watermark_robust_pareto_export(art)
    assert "diagnostic" in str(out["rows"][0]["robust_Q_DT_eqv"]).lower()
    nom = out["points"][0]["nominal_outputs"]
    assert "diagnostic" in str(nom["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(nom["H98"]).lower()
    assert nom["R0_m"] == 6.0
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note", ""))


def test_external_robust_view_wires_physkpi():
    src = Path("ui_nicegui/decks/pareto_lab/external.py").read_text(encoding="utf-8")
    assert "watermark_robust_pareto_rows" in src
    assert "watermark_robust_pareto_export" in src
    assert "allow_infeasible_scatter_point" in src
    assert "PHYS-KPI-001" in src
    assert 'str(tier).upper() == "FAIL"' in src
