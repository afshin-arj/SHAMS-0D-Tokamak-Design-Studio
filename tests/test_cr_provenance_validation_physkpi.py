"""Control Room provenance + validation envelope PHYS-KPI honesty."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_watermark_envelope_rows_infeasible():
    from ui_nicegui.decks.control_room.validation_envelopes import watermark_envelope_rows

    rows = [
        {"metric": "Q_DT_eqv", "value": 12.0, "lo": 5.0, "hi": 50.0, "ok": True},
        {"metric": "beta_N", "value": 2.5, "lo": 1.0, "hi": 4.0, "ok": True},
    ]
    out = watermark_envelope_rows(rows, feasible=False)
    assert "diagnostic" in str(out[0]["value"]).lower()
    assert out[1]["value"] == 2.5


def test_regression_artifact_diff_watermarks_claim_kpis():
    from ui_nicegui.lib.cr_provenance_helpers import regression_artifact_diff

    # Minimal infeasible-looking artifacts: empty governance via impossible outputs is hard;
    # force via constraints that make verdict_summary infeasible when possible.
    # Prefer explicit outputs that fail hard constraints — use empty dict → not loaded/feasible False.
    a = {
        "outputs": {},
        "kpis": {"Q_DT_eqv": 10.0, "beta_N": 2.0},
        "constraints": [],
    }
    b = {
        "outputs": {},
        "kpis": {"Q_DT_eqv": 12.0, "beta_N": 2.1},
        "constraints": [{"name": "q95", "failed": True, "passed": False, "severity": "hard", "margin": -0.1}],
    }
    # Empty outputs → feasible False via verdict_summary loaded False / not feasible
    d = regression_artifact_diff(a, b)
    qrow = next(r for r in d["kpi_rows"] if r["kpi"] == "Q_DT_eqv")
    assert "diagnostic" in str(qrow["value_A"]).lower()
    assert "diagnostic" in str(qrow["value_B"]).lower()
    brow = next(r for r in d["kpi_rows"] if r["kpi"] == "beta_N")
    assert brow["value_A"] == 2.0


def test_regression_soft_fail_not_new_failure():
    from ui_nicegui.lib.cr_provenance_helpers import regression_artifact_diff

    a = {"outputs": {"Q": 1.0}, "constraints": [{"name": "soft", "failed": False, "passed": True, "severity": "diagnostic"}]}
    b = {
        "outputs": {"Q": 1.0},
        "constraints": [
            {"name": "soft", "failed": True, "passed": False, "severity": "diagnostic", "margin": -1.0}
        ],
    }
    d = regression_artifact_diff(a, b)
    assert d["new_failures"] == []


def test_governance_q_label_diagnostic_on_infeasible():
    from ui_nicegui.lib.control_room_helpers import governance_summary

    session = SimpleNamespace(
        pd_last_outputs={"Q_DT_eqv": 9.0, "H98": 1.2},  # likely infeasible without full constraint pass
        pd_last_artifact={"kpis": {"feasible_hard": False}},
        design_intent="Reactor",
        active_deck="Control Room",
        pd_last_run_ts=None,
    )
    # Patch verdict via real summary — if this point is somehow feasible, still assert shape.
    # Force path: mock by using outputs that trigger governance fail is hard; use helper directly.
    from ui_nicegui.lib import control_room_helpers as h
    from ui_nicegui.lib import verdict_core

    real = verdict_core.verdict_summary

    def _fake(out):
        return {"loaded": True, "feasible": False, "verdict": "INFEASIBLE", "dominant": "x", "q_label": "Q=9.00"}

    verdict_core.verdict_summary = _fake  # type: ignore
    try:
        s = h.governance_summary(session)
        assert s["q_label"] == "— (diagnostic)"
        assert s["pfus_label"] == "— (diagnostic)"
    finally:
        verdict_core.verdict_summary = real  # type: ignore


def test_ui_wires_physkpi_banners():
    vsrc = Path("ui_nicegui/decks/control_room/validation_envelopes.py").read_text(encoding="utf-8")
    assert "watermark_envelope_rows" in vsrc
    assert "PHYS-KPI-001" in vsrc
    psrc = Path("ui_nicegui/decks/control_room/provenance.py").read_text(encoding="utf-8")
    assert "PHYS-KPI-001" in psrc
    assert "feasible_A" in psrc
