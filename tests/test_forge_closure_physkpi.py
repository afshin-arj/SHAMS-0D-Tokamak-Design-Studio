"""Forge closure / report-pack PHYS-KPI-001 honesty on INFEASIBLE candidates."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_net_electric_is_claim_kpi():
    from ui_nicegui.lib.plant_kpi_honesty_ui import format_claim_kpi_for_table, is_claim_kpi_key

    assert is_claim_kpi_key("net_electric_MW")
    assert "diagnostic" in format_claim_kpi_for_table(
        "net_electric_MW", 120.0, feasible=False
    ).lower()


def test_watermark_forge_closure_and_report_pack():
    from ui_nicegui.lib.forge_interpret_helpers import (
        watermark_forge_closure_bundle,
        watermark_forge_report_pack,
    )

    cb = watermark_forge_closure_bundle(
        {"net_electric_MW": 100.0, "recirc_electric_MW": 40.0, "gross_electric_MW": 140.0},
        feasible=False,
    )
    assert "diagnostic" in str(cb["net_electric_MW"]).lower()
    assert cb["recirc_electric_MW"] == 40.0

    ok = watermark_forge_closure_bundle({"net_electric_MW": 100.0}, feasible=True)
    assert ok["net_electric_MW"] == 100.0

    rp = watermark_forge_report_pack(
        {
            "markdown": "## Closure (summary)\n- net_electric_MW: 100.0\n",
            "json": {
                "feasible": False,
                "key_outputs": {"Q_DT_eqv": 12.0, "P_e_net_MW": 100.0, "R0_m": 6.0},
                "closure_bundle": {"net_electric_MW": 100.0},
                "closure_certificate": {
                    "verdict": "FAIL",
                    "key_numbers": {"net_electric_MW": 100.0},
                    "notes": [],
                },
            },
        },
        feasible=False,
        point_out={"Q_DT_eqv": 12.0, "P_e_net_MW": 100.0},
    )
    j = rp["json"]
    assert "diagnostic" in str(j["key_outputs"]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(j["closure_bundle"]["net_electric_MW"]).lower()
    assert "diagnostic" in str(j["closure_certificate"]["key_numbers"]["net_electric_MW"]).lower()
    assert j["key_outputs"]["R0_m"] == 6.0
    assert "PHYS-KPI-001" in rp["markdown"]
    assert "PHYS-KPI-001" in str(rp.get("phys_kpi_note", ""))


def test_enrich_passes_feasible_and_watermarks():
    src = Path("ui_nicegui/lib/forge_interpret_helpers.py").read_text(encoding="utf-8")
    assert "feasible=feasible" in src
    assert "watermark_forge_closure_bundle" in src
    assert "watermark_forge_report_pack" in src

    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "watermark_forge_closure_bundle" in eng
    assert "watermark_forge_report_pack" in eng
    assert "export_doi_ready_pack(" in eng
    assert "run_meta=" in eng
    assert "archive_rows=" in eng
    assert "watermark_extopt_zip_bytes" in eng
    assert "run=ctx.run" not in eng

    wb = Path("ui_nicegui/decks/reactor_design_forge/workbench.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001: Closure / report claim FoMs" in wb
