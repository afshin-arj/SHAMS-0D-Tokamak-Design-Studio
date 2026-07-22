"""Control Room knob trade-space: hard feasibility + PHYS-KPI table watermarking."""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_evaluate_knob_trade_grid_uses_verdict_summary():
    from ui_nicegui.lib import cr_chronicle_helpers as h

    src = inspect.getsource(h.evaluate_knob_trade_grid)
    assert "verdict_summary" in src
    assert "evaluate_constraints" not in src
    assert "H98" in src
    assert "P_e_net_MW" in src


def test_watermark_knob_grid_rows_suppresses_claims():
    from ui_nicegui.decks.control_room.knob_trade_space import watermark_knob_grid_rows

    rows = [
        {
            "Ip_MA": 8.0,
            "fG": 0.8,
            "feasible": False,
            "top_blocker": "q_div",
            "Q": 12.0,
            "H98": 1.1,
            "Pfus_total_MW": 200.0,
            "P_e_net_MW": 50.0,
        },
        {
            "Ip_MA": 8.1,
            "fG": 0.81,
            "feasible": True,
            "top_blocker": None,
            "Q": 2.5,
            "H98": 1.05,
            "Pfus_total_MW": 100.0,
            "P_e_net_MW": 40.0,
        },
    ]
    disp = watermark_knob_grid_rows(rows, kx="Ip_MA", ky="fG")
    assert "diagnostic" in str(disp[0]["Q"]).lower()
    assert "diagnostic" in str(disp[0]["H98"]).lower()
    assert "diagnostic" in str(disp[0]["Pfus_total_MW"]).lower()
    assert "diagnostic" in str(disp[0]["P_e_net_MW"]).lower()
    assert "diagnostic" not in str(disp[1]["Q"]).lower()
    assert "2.5" in str(disp[1]["Q"])


def test_knob_trade_space_ui_wires_watermark_helper():
    src = Path("ui_nicegui/decks/control_room/knob_trade_space.py").read_text(encoding="utf-8")
    assert "watermark_knob_grid_rows" in src
    assert "format_claim_kpi_for_table" in src
    assert "from dataclasses import replace\n\nfrom dataclasses import replace" not in src


def test_pd_physics_deepening_watermarks_h98():
    src = Path("ui_nicegui/decks/point_designer/pd_physics_deepening.py").read_text(encoding="utf-8")
    assert "_claim_disp" in src
    assert '("H98(y,2)", _claim_disp(out, "H98"' in src
