"""Control Room scenario-delta + artifacts PHYS-KPI honesty (helm-decks loop)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_changed_kpis_table_rows_watermarks_infeasible():
    from ui_nicegui.lib.plant_kpi_honesty_ui import changed_kpis_table_rows

    changed = {
        "Q": {"base": 5.0, "scenario": 6.0},
        "beta_N": {"base": 2.0, "scenario": 2.1},
    }
    rows = changed_kpis_table_rows(changed, feasible_base=False, feasible_scenario=True)
    by = {r["kpi"]: r for r in rows}
    assert "diagnostic" in str(by["Q"]["baseline"]).lower()
    assert "diagnostic" not in str(by["Q"]["scenario"]).lower()
    assert by["Q"]["delta"] == "— (diagnostic)"
    assert by["beta_N"]["baseline"] == 2.0
    assert abs(float(by["beta_N"]["delta"]) - 0.1) < 1e-9


def test_watermark_claim_kpi_map_plasma_table():
    from ui_nicegui.lib.plant_kpi_honesty_ui import watermark_claim_kpi_map

    block = {"H98": 1.2, "Q_DT_eqv": 8.0, "beta_N": 2.5, "Ti_keV": 12.0}
    out = watermark_claim_kpi_map(block, feasible=False)
    assert "diagnostic" in str(out["H98"]).lower()
    assert "diagnostic" in str(out["Q_DT_eqv"]).lower()
    assert out["beta_N"] == 2.5
    assert out["Ti_keV"] == 12.0


def test_constraint_margin_soft_fail_not_new_failure():
    from ui_nicegui.lib.compare_helpers import constraint_margin_diff_rows

    a = {
        "constraints": [
            {"name": "diag_soft", "failed": False, "passed": True, "margin": 0.2, "severity": "diagnostic"}
        ]
    }
    b = {
        "constraints": [
            {
                "name": "diag_soft",
                "failed": True,
                "passed": False,
                "margin": -0.1,
                "severity": "diagnostic",
            }
        ]
    }
    rows = constraint_margin_diff_rows(a, b)
    assert rows[0]["new_failure"] is False
    assert rows[0]["failed_B"] is False
    assert rows[0]["soft_failed_B"] is True
    assert rows[0]["severity_B"] == "diagnostic"


def test_constraint_margin_hard_fail_still_new_failure():
    from ui_nicegui.lib.compare_helpers import constraint_margin_diff_rows

    a = {"constraints": [{"name": "q95", "failed": False, "margin": 0.2, "passed": True}]}
    b = {
        "constraints": [
            {"name": "q95", "failed": True, "margin": -0.1, "passed": False, "severity": "hard"}
        ]
    }
    rows = constraint_margin_diff_rows(a, b)
    assert rows[0]["new_failure"] is True
    assert rows[0]["failed_B"] is True


def test_scenario_delta_ui_wires_physkpi():
    src = Path("ui_nicegui/decks/control_room/scenario_delta.py").read_text(encoding="utf-8")
    assert "changed_kpis_table_rows" in src
    assert "PHYS-KPI-001" in src
    assert "verdict_summary" in src


def test_artifacts_ui_wires_physkpi():
    src = Path("ui_nicegui/decks/control_room/artifacts.py").read_text(encoding="utf-8")
    assert "watermark_claim_kpi_map" in src
    assert "PHYS-KPI-001" in src
    assert "plasma" in src and "power_balance" in src
