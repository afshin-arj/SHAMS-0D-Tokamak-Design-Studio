"""Trade Study + Scan contour PHYS-KPI honesty (helm-decks loop)."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_claim_key_for_objective_column_maps_foms():
    from ui_nicegui.lib.plant_kpi_honesty_ui import claim_key_for_objective_column

    assert claim_key_for_objective_column("max_Q") == "Q_DT_eqv"
    assert claim_key_for_objective_column("max_H98") == "H98"
    assert claim_key_for_objective_column("max_Pnet") == "P_e_net_MW"
    assert claim_key_for_objective_column("min_COE") == "COE_proxy_USD_per_MWh"
    assert claim_key_for_objective_column("min_R0") is None


def test_watermark_trade_study_table_rows():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_trade_study_table_rows

    rows = [
        {"i": 0, "is_feasible": False, "max_Q": 12.0, "min_R0": 6.0, "R0_m": 6.0},
        {"i": 1, "is_feasible": True, "max_Q": 3.5, "min_R0": 5.5, "R0_m": 5.5},
    ]
    cols = ["i", "is_feasible", "max_Q", "min_R0", "R0_m"]
    out = watermark_trade_study_table_rows(rows, cols)
    assert "diagnostic" in str(out[0]["max_Q"]).lower()
    assert out[0]["min_R0"] == 6.0  # geometry FoM not a claim KPI
    assert "diagnostic" not in str(out[1]["max_Q"]).lower()


def test_trade_study_results_wires_watermark():
    src = Path("ui_nicegui/decks/trade_study_studio/results.py").read_text(encoding="utf-8")
    assert "watermark_trade_study_table_rows" in src
    assert "PHYS-KPI-001" in src


def test_scan_contour_masks_infeasible_claim_cells():
    from ui_nicegui.lib.scan_workbench_helpers import plotly_contour_figure

    rep = {
        "x_key": "R0_m",
        "y_key": "Bt_T",
        "x_vals": [5.0, 6.0],
        "y_vals": [4.0],
        "points": [
            {
                "i": 0,
                "j": 0,
                "outputs": {"Q_DT_eqv": 10.0},
                "intent": {"DEMO": {"blocking_feasible": False}},
            },
            {
                "i": 1,
                "j": 0,
                "outputs": {"Q_DT_eqv": 2.0},
                "intent": {"DEMO": {"blocking_feasible": True}},
            },
        ],
    }
    fig = plotly_contour_figure(rep, "DEMO", "Q_DT_eqv")
    z = fig.data[0].z
    assert math.isnan(float(z[0][0]))
    assert float(z[0][1]) == 2.0
    assert "feasible" in str(fig.layout.title.text).lower() or "diagnostic" in str(fig.layout.title.text).lower()


def test_scan_workbench_wires_physkpi_contour_banner():
    src = Path("ui_nicegui/decks/scan_lab/workbench.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001" in src
    assert "is_claim_kpi_key" in src


def test_forge_review_trinity_wires_watermark():
    src = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "format_claim_kpi_for_table" in src
    # Review trinity path must watermark when infeasible
    assert "_inst_review_trinity" in src
    assert "PHYS-KPI-001: claim KPIs below are diagnostic" in src
