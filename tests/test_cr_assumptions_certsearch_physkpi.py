"""Control Room assumptions + certified-search PHYS-KPI / hard-feasibility honesty."""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_cert_search_verifier_uses_verdict_summary():
    from ui_nicegui.lib import cr_chronicle_helpers as h

    src = inspect.getsource(h.run_orchestrated_certified_search_nicegui)
    assert "verdict_summary" in src
    assert "constraint_is_hard" in src
    # Soft fails must not set failed=True for Pareto orchestrator path.
    assert "soft_fail and hard" in src or "failed and hard" in src


def test_assumptions_panel_watermarks_claim_kpis():
    src = Path("ui_nicegui/decks/control_room/assumptions_panel.py").read_text(encoding="utf-8")
    assert "format_claim_kpi_for_table" in src
    assert "PHYS-KPI-001" in src
    assert "point is INFEASIBLE" in src


def test_watermark_certified_search_rows():
    from ui_nicegui.decks.control_room.certified_search import watermark_certified_search_rows

    rows = [
        {
            "stage": "s1",
            "verdict": "FAIL",
            "score": 12.0,
            "e_objective_value": 12.0,
            "e_objective": "Q_DT_eqv",
            "Q_DT_eqv": 12.0,
            "P_e_net_MW": 50.0,
        },
        {
            "stage": "s1",
            "verdict": "PASS",
            "score": 2.5,
            "Q_DT_eqv": 2.5,
            "P_e_net_MW": 40.0,
        },
    ]
    disp = watermark_certified_search_rows(rows)
    assert "diagnostic" in str(disp[0]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(disp[0]["score"]).lower()
    assert "diagnostic" in str(disp[0]["e_objective_value"]).lower()
    assert "diagnostic" not in str(disp[1]["Q_DT_eqv"]).lower()


def test_certified_search_ui_wires_watermark():
    src = Path("ui_nicegui/decks/control_room/certified_search.py").read_text(encoding="utf-8")
    assert "watermark_certified_search_rows" in src
    assert "PHYS-KPI-001" in src
