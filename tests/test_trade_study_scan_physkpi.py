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
    # Source builder owns PHYS-KPI-001; NiceGUI surfaces its markdown/JSON.
    src = Path("tools/sandbox/review_room.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001" in src
    assert "_watermark_closure" in src
    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "_inst_review_trinity" in eng
    assert "build_review_trinity" in eng


def test_watermark_scan_cartography_export_masks_q_on_infeasible():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_scan_cartography_export

    rep = {
        "points": [
            {
                "i": 0,
                "j": 0,
                "outputs": {"Q": 10.0, "H98": 1.2, "R0_m": 5.0},
                "intent": {"Reactor": {"blocking_feasible": False}},
            },
            {
                "i": 1,
                "j": 0,
                "outputs": {"Q": 3.0, "H98": 0.9},
                "intent": {"Reactor": {"blocking_feasible": True}},
            },
        ]
    }
    out = watermark_scan_cartography_export(rep)
    assert "diagnostic" in str(out["points"][0]["outputs"]["Q"]).lower()
    assert "diagnostic" in str(out["points"][0]["outputs"]["H98"]).lower()
    assert out["points"][0]["outputs"]["R0_m"] == 5.0
    assert "diagnostic" not in str(out["points"][1]["outputs"]["Q"]).lower()
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note") or "")


def test_scan_export_archive_wires_watermark_scan_cartography():
    src = Path("ui_nicegui/decks/scan_lab/export_archive.py").read_text(encoding="utf-8")
    assert "watermark_scan_cartography_export" in src
    res = Path("ui_nicegui/decks/scan_lab/results.py").read_text(encoding="utf-8")
    assert "watermark_scan_cartography_export" in res


def test_watermark_pareto_artifact_export_masks_infeasible():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_pareto_artifact_export

    art = {
        "pareto": [
            {"feasible": False, "Q_DT_eqv": 8.0, "R0_m": 4.0, "outputs": {"Q": 8.0}},
            {"feasible": True, "Q_DT_eqv": 2.5, "R0_m": 5.0},
            {"verdict": "INFEASIBLE", "H98": 1.1},
        ]
    }
    out = watermark_pareto_artifact_export(art)
    assert "diagnostic" in str(out["pareto"][0]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(out["pareto"][0]["outputs"]["Q"]).lower()
    assert out["pareto"][0]["R0_m"] == 4.0
    assert "diagnostic" not in str(out["pareto"][1]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(out["pareto"][2]["H98"]).lower()
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note") or "")


def test_systems_export_ui_wires_watermark_run_artifact_for_pdfs():
    src = Path("ui_nicegui/decks/systems_mode/export_ui.py").read_text(encoding="utf-8")
    assert "watermark_run_artifact_export" in src
    assert "build_decision_report_pdf_bytes" in src
    assert "build_executive_summary_pdf_bytes" in src
    assert "PHYS-KPI-001" in src
