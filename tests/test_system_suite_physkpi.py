"""System Suite campaign / pulse PHYS-KPI honesty."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_campaign_results_to_atlas_watermarks_infeasible():
    from ui_nicegui.lib.suite_helpers import campaign_results_to_atlas_records

    records = [
        {
            "cid": "a",
            "feasible_hard": False,
            "dominant_mechanism": "exhaust",
            "artifact": {
                "outputs": {"Q_DT_eqv": 12.0, "H98": 1.5, "beta_N": 2.0, "R0_m": 6.0},
                "kpis": {"P_e_net_MW": 100.0},
            },
        },
        {
            "cid": "b",
            "feasible_hard": True,
            "dominant_mechanism": "",
            "artifact": {
                "outputs": {"Q_DT_eqv": 3.0, "H98": 1.1},
                "kpis": {"P_e_net_MW": 40.0},
            },
        },
    ]
    out = campaign_results_to_atlas_records(preview_rows=records)
    by = {r["cid"]: r for r in out}
    assert "diagnostic" in str(by["a"]["Q_DT_eqv"]).lower()
    assert "diagnostic" in str(by["a"]["P_e_net_MW"]).lower()
    assert by["a"]["beta_N"] == 2.0
    assert "diagnostic" not in str(by["b"]["Q_DT_eqv"]).lower()
    assert by["a"]["robustness_class"] == "infeasible"
    assert by["b"]["robustness_class"] == "robust"


def test_watermark_campaign_preview_rows():
    from ui_nicegui.lib.suite_extended_helpers import watermark_campaign_preview_rows

    rows = [
        {"cid": "1", "feasible_hard": False, "Q_DT_eqv": 9.0, "R0_m": 6.0},
        {"cid": "2", "feasible_hard": True, "Q_DT_eqv": 2.0, "R0_m": 5.0},
    ]
    out = watermark_campaign_preview_rows(rows)
    assert "diagnostic" in str(out[0]["Q_DT_eqv"]).lower()
    assert out[0]["R0_m"] == 6.0
    assert "diagnostic" not in str(out[1]["Q_DT_eqv"]).lower()


def test_suite_tabs_omit_pnet_trace_on_infeasible():
    src = Path("ui_nicegui/decks/system_suite/tabs.py").read_text(encoding="utf-8")
    assert "P_net omitted on INFEASIBLE" in src or "P_net_MW omitted" in src or "recirc only" in src
    assert "PHYS-KPI-001: net-electric pulse trace omitted" in src
    assert "watermark_campaign_preview_rows" in src
