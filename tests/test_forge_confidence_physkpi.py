"""Forge Confidence Sweep PHYS-KPI-001 honesty on INFEASIBLE candidates."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _records_ok():
    return [
        {"name": "q95", "signed_margin": 0.2},
        {"name": "betaN", "signed_margin": 0.1},
    ]


def _closure():
    return {
        "gross_electric_MW": 140.0,
        "recirc_electric_MW": 40.0,
        "net_electric_MW": 100.0,
        "economics_envelopes": {"Nominal": {"LCOE_proxy": 80.0}},
    }


def test_confidence_sweep_watermarks_net_on_infeasible():
    from tools.sandbox.confidence_sweep import confidence_sweep

    out = confidence_sweep(_records_ok(), closure_bundle=_closure(), feasible=False)
    assert out["ok"] is True
    assert out["feasible"] is False
    assert out["proxy_headlines"]
    for row in out["proxy_headlines"]:
        assert row["net_electric_MW"] == "— (diagnostic)"
        assert row["nominal_LCOE_proxy"] == "— (diagnostic)"
    assert "PHYS-KPI-001" in (out.get("notes") or {}).get("phys_kpi_note", "")


def test_confidence_sweep_keeps_net_when_feasible():
    from tools.sandbox.confidence_sweep import confidence_sweep

    out = confidence_sweep(_records_ok(), closure_bundle=_closure(), feasible=True)
    assert out["feasible"] is True
    assert out["proxy_headlines"][0]["net_electric_MW"] == 100.0
    assert "phys_kpi_note" not in (out.get("notes") or {})


def test_confidence_sweep_default_feasible_preserves_legacy():
    """Omit feasible= → treat as claim-ok (legacy callers / margin-only sweeps)."""
    from tools.sandbox.confidence_sweep import confidence_sweep

    out = confidence_sweep(_records_ok(), closure_bundle=_closure())
    assert out["proxy_headlines"][0]["net_electric_MW"] == 100.0


def test_inst_confidence_sweep_wiring():
    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "closure_bundle=closure" in eng
    assert "feasible=feasible" in eng
    assert "archive=ctx.archive" not in eng.split("_inst_confidence_sweep")[1].split("def _inst_")[0]
    assert "PHYS-KPI-001: proxy_headlines net electric" in eng
