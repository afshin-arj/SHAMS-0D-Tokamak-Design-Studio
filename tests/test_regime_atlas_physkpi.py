"""Regime Atlas PHYS-KPI-001 — hard-fail exclusion + evidence watermark."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_hard_infeasible_excluded_from_optimistic_gate():
    from analysis.regime_conditioned_atlas_v365 import (
        AtlasConfig,
        MetricSpec,
        build_regime_conditioned_atlas,
    )

    recs = [
        {
            "candidate_id": "hard_fail",
            "feasible_hard": False,
            "feasible": True,
            "optimistic_feasible": True,
            "robust_feasible": False,
            "verdict": "INFEASIBLE",
            "plasma_regime": "H-mode",
            "exhaust_regime": "detached",
            "dominance_label": "PLASMA",
            "outputs": {"P_e_net_MW": 100.0, "f_recirc": 0.3, "CoE_USD_MWh": 90.0},
        },
        {
            "candidate_id": "ok",
            "feasible_hard": True,
            "optimistic_feasible": True,
            "robust_feasible": True,
            "plasma_regime": "H-mode",
            "exhaust_regime": "detached",
            "dominance_label": "PLASMA",
            "outputs": {"P_e_net_MW": 50.0, "f_recirc": 0.25, "CoE_USD_MWh": 80.0},
        },
    ]
    cfg = AtlasConfig(
        conditioning_axes=("plasma_regime", "exhaust_regime", "dominance_label", "robustness_class"),
        min_bucket_size=1,
        feasibility_gate="optimistic",
        metrics=(
            MetricSpec("P_e_net_MW", "max"),
            MetricSpec("f_recirc", "min"),
            MetricSpec("CoE_USD_MWh", "min"),
        ),
    )
    atlas = build_regime_conditioned_atlas(recs, cfg)
    ids = {row.get("candidate_id") for row in atlas.get("pareto_sets", [])}
    assert "hard_fail" not in ids
    assert "ok" in ids


def test_verdict_infeasible_excluded_without_feasible_hard_flag():
    from analysis.regime_conditioned_atlas_v365 import _is_feasible

    assert _is_feasible({"verdict": "INFEASIBLE", "optimistic_feasible": True}, "optimistic") is False
    assert _is_feasible({"feasible_hard": False, "optimistic_feasible": True}, "any_feasible") is False
    assert _is_feasible({"feasible_hard": True, "optimistic_feasible": True}, "optimistic") is True


def test_watermark_regime_atlas_export():
    from ui_nicegui.lib.plant_kpi_honesty_ui import (
        is_claim_kpi_key,
        watermark_regime_atlas_export,
    )

    assert is_claim_kpi_key("CoE_USD_MWh")
    art = {
        "schema": "shams_regime_conditioned_atlas.v365",
        "pareto_sets": [
            {
                "candidate_id": "x",
                "robustness_class": "INFEASIBLE",
                "metrics": {"P_e_net_MW": 120.0, "f_recirc": 0.4, "CoE_USD_MWh": 99.0},
            }
        ],
    }
    out = watermark_regime_atlas_export(art)
    m = out["pareto_sets"][0]["metrics"]
    assert "diagnostic" in str(m["P_e_net_MW"]).lower()
    assert "diagnostic" in str(m["CoE_USD_MWh"]).lower()
    assert m["f_recirc"] == 0.4
    assert "PHYS-KPI-001" in str(out.get("phys_kpi_note", ""))


def test_atlas_ui_and_zip_wire_physkpi():
    ext = Path("ui_nicegui/decks/pareto_lab/external.py").read_text(encoding="utf-8")
    assert "hard-infeasible records are excluded" in ext
    assert "PHYS-KPI-001" in ext
    helpers = Path("ui_nicegui/lib/external_optimizer_helpers.py").read_text(encoding="utf-8")
    assert "watermark_regime_atlas_export" in helpers
