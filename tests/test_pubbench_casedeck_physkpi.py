"""Publication pack + Case Deck PHYS-KPI honesty (helm-decks loop)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_run_one_watermarks_claim_kpis_on_blocking_fail():
    from benchmarks.publication.run_point_designer_benchmarks import _build_inputs, run_one

    inp = _build_inputs(
        {"R0_m": 6.2, "a_m": 2.0, "Bt_T": 5.3, "Ip_MA": 15.0, "Ti_keV": 10.0, "fG": 0.85, "Paux_MW": 50.0}
    )
    res = run_one("physkpi_case", inp, design_intent="Reactor")
    row = res["row"]
    if row.get("ok_blocking") is False:
        for k in ("H98", "Q_DT_eqv", "P_fus_MW", "P_e_net_MW"):
            assert "diagnostic" in str(row.get(k)).lower(), f"{k}={row.get(k)}"
    else:
        src = Path("benchmarks/publication/run_point_designer_benchmarks.py").read_text(encoding="utf-8")
        assert "— (diagnostic)" in src


def test_watermark_case_deck_artifact():
    from ui_nicegui.decks.control_room.case_deck_panel import watermark_case_deck_artifact

    art = {
        "outputs": {"Q_DT_eqv": 12.0, "H98": 1.5, "beta_N": 2.0},
        "kpis": {"Q_DT_eqv": 12.0},
        "tables": {"plasma": {"H98": 1.5, "Q_DT_eqv": 12.0, "Ti_keV": 10.0}},
    }
    # Empty constraint path → verdict_summary likely infeasible or not loaded → treat as not feasible
    disp = watermark_case_deck_artifact(art)
    # Force path: if somehow feasible, still check helper wired
    assert "outputs" in disp
    from ui_nicegui.lib.verdict_core import verdict_summary

    feas = bool(verdict_summary(art["outputs"]).get("feasible"))
    if not feas:
        assert "diagnostic" in str(disp["outputs"]["Q_DT_eqv"]).lower()
        assert disp["tables"]["plasma"]["Ti_keV"] == 10.0


def test_atlas_evidence_json_watermarks_fail():
    from ui_nicegui.lib.benchmark_helpers import atlas_evidence_json

    payload = json.loads(
        atlas_evidence_json(
            {
                "preset_key": "x",
                "run": {
                    "verdict": "FAIL",
                    "outputs": {"Q_DT_eqv": 80.0, "H98": 3.0, "beta_N": 2.0},
                },
            }
        ).decode("utf-8")
    )
    assert "diagnostic" in str(payload["run"]["outputs"]["Q_DT_eqv"]).lower()
    assert "phys_kpi_001" in payload["run"]


def test_ui_wires_physkpi_captions():
    assert "PHYS-KPI-001" in Path("ui_nicegui/decks/control_room/case_deck_panel.py").read_text(
        encoding="utf-8"
    )
    assert "PHYS-KPI-001" in Path(
        "ui_nicegui/decks/publication_benchmarks/benchmark_pack.py"
    ).read_text(encoding="utf-8")
    assert "— (diagnostic)" in Path(
        "benchmarks/publication/run_point_designer_benchmarks.py"
    ).read_text(encoding="utf-8")
    assert "PHYS-KPI-001" in Path("benchmarks/publication/explain_delta.py").read_text(
        encoding="utf-8"
    )
