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


def test_control_room_cite_pack_uses_watermark_run_artifact():
    src = Path("ui_nicegui/decks/control_room/artifacts.py").read_text(encoding="utf-8")
    assert "build_cite_shams_handoff_pack(watermark_run_artifact_export(art))" in src


def test_systems_export_bytes_watermarks_run_cards_payload():
    import json

    from ui_nicegui.lib.systems_workflow_helpers import systems_export_bytes
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.systems_run_cards = [
        {
            "id": "c1",
            "kind": "solve",
            "outcome": {"ok": False},
            "payload": {
                "verdict": "INFEASIBLE",
                "outputs": {
                    "Q_DT_eqv": 12.0,
                    "hard_feasible": False,
                    "constraints_failed": ["greenwald"],
                },
            },
        },
        {
            "id": "c2",
            "kind": "search",
            "outcome": {"ok": False, "feasible": False},
            "payload": {"headline": {"Q_DT_eqv": 9.0, "R0_m": 6.0}, "metrics": {"H98": 1.2}},
        },
    ]
    data = json.loads(systems_export_bytes(s).decode("utf-8"))
    cards = data["systems_run_cards"]
    outs = cards[0]["payload"]["outputs"]
    assert "diagnostic" in str(outs.get("Q_DT_eqv")).lower()
    assert "diagnostic" in str(cards[1]["payload"]["headline"].get("Q_DT_eqv")).lower()
    assert cards[1]["payload"]["headline"]["R0_m"] == 6.0
    assert "diagnostic" in str(cards[1]["payload"]["metrics"].get("H98")).lower()
    assert "PHYS-KPI-001" in str(data.get("phys_kpi_note") or "")


def test_deck_busy_guard_pub_and_systems_atlas_attrs():
    from ui_nicegui.lib.deck_busy_guard import PUB_RUNNING_ATTRS, SYSTEMS_RUNNING_ATTRS

    assert "pub_running" in PUB_RUNNING_ATTRS
    assert "pub_atlas_running" in PUB_RUNNING_ATTRS
    assert "pub_atlas_fragility_running" in PUB_RUNNING_ATTRS
    assert "pub_bench_running" in PUB_RUNNING_ATTRS
    assert "systems_atlas_running" in SYSTEMS_RUNNING_ATTRS
    pub_src = Path("ui_nicegui/decks/publication_benchmarks/__init__.py").read_text(encoding="utf-8")
    assert "PUB_RUNNING_ATTRS" in pub_src
    assert "refresh_tab_if_idle" in pub_src
    sys_src = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "SYSTEMS_RUNNING_ATTRS" in sys_src


def test_cartography_activates_progress_timer_when_scan_running_on_remount():
    src = Path("ui_nicegui/decks/scan_lab/cartography.py").read_text(encoding="utf-8")
    # After remount mid-scan: disable btns AND re-activate progress timer + refresh panel.
    assert "if session.scan_running:" in src
    block = src.split("if session.scan_running:")[-1]
    assert "_progress_timer.activate()" in block
    assert "_scan_progress_panel.refresh()" in block


def test_field_cube_download_uses_wm_rep():
    src = Path("ui_nicegui/decks/scan_lab/export_archive.py").read_text(encoding="utf-8")
    assert "wm_rep = watermark_scan_cartography_export(rep)" in src
    assert "field_cube_json_bytes(wm_rep)" in src
    assert "field_cube_json_bytes(rep)" not in src


def test_watermark_scan_cartography_blanks_field_cube_claim_vars():
    import math

    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_scan_cartography_export

    rep = {
        "points": [
            {
                "i": 0,
                "j": 0,
                "outputs": {"Q_DT_eqv": 10.0},
                "intent": {"Reactor": {"blocking_feasible": False}},
            },
            {
                "i": 1,
                "j": 0,
                "outputs": {"Q_DT_eqv": 2.0},
                "intent": {"Reactor": {"blocking_feasible": True}},
            },
        ],
        "field_cube": {
            "schema": "shams_field_cube.v1",
            "dims": {"x": 2, "y": 1},
            "intent_vars": {
                "Reactor": {"blocking_feasible": [[False, True]]},
            },
            "vars": {
                "Q_DT_eqv": [[10.0, 2.0]],
                "R0_m": [[5.0, 6.0]],
            },
        },
    }
    out = watermark_scan_cartography_export(rep)
    q = out["field_cube"]["vars"]["Q_DT_eqv"]
    assert math.isnan(float(q[0][0]))
    assert float(q[0][1]) == 2.0
    assert out["field_cube"]["vars"]["R0_m"][0][0] == 5.0
    assert "PHYS-KPI-001" in str(out["field_cube"].get("phys_kpi_note") or "")


def test_watermark_run_artifact_export_tables_plasma_power_balance():
    from ui_nicegui.lib.cr_artifacts_helpers import watermark_run_artifact_export

    art = {
        "verdict": "INFEASIBLE",
        "outputs": {
            "Q_DT_eqv": 9.0,
            "hard_feasible": False,
            "constraints_failed": ["x"],
        },
        "tables": {
            "v1": {
                "plasma": {"Q_DT_eqv": 9.0, "Ip_MA": 8.0},
                "power_balance": {"H98": 1.1, "R0_m": 5.0},
            }
        },
    }
    wa = watermark_run_artifact_export(art)
    plasma = wa["tables"]["v1"]["plasma"]
    pb = wa["tables"]["v1"]["power_balance"]
    assert "diagnostic" in str(plasma["Q_DT_eqv"]).lower()
    assert plasma["Ip_MA"] == 8.0 or "8" in str(plasma["Ip_MA"])
    assert "diagnostic" in str(pb["H98"]).lower()
    assert pb["R0_m"] == 5.0


def test_pub_licensing_regulatory_evidence_wire_watermark():
    ext = Path("ui_nicegui/lib/pub_benchmark_extended_helpers.py").read_text(encoding="utf-8")
    assert "watermark_run_artifact_export" in ext
    # licensing + regulatory stamp before pack
    assert ext.count("art = watermark_run_artifact_export(art)") >= 2
    assert "watermark_scan_cartography_export" in ext
    assert "phys_kpi_note" in ext
    assert "build_evidence_pack_v387" in ext
