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
    # H98 must be in displayed keys (aliases alone are dead code).
    assert '"H98"' in src or "'H98'" in src
    assert "H_IPB98y2" in src
    assert "Q / H98 / Pfus / P_net" in src
    assert "design_intent" in src


def test_magnet_card_pe_net_passes_artifact_intent():
    src = Path("ui_nicegui/decks/point_designer/mission_snapshot.py").read_text(encoding="utf-8")
    assert "def _magnet_card" in src
    assert "pe_net_display(out, artifact=artifact, design_intent=design_intent)" in src
    assert "_magnet_card(out, artifact=art, design_intent=str(session.design_intent))" in src


def test_chronicle_sensitivity_selectors_label_claim_outputs():
    src = Path("ui_nicegui/decks/control_room/chronicle.py").read_text(encoding="utf-8")
    assert "_SENS_OUTPUT_OPTIONS" in src
    assert "H98 (claim)" in src
    assert "beta_N (screening)" in src
    assert "TBR (proxy)" in src
    assert "claim-KPI jacobians are diagnostic" in src


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
    assert "promote_certified_search_x_to_point_designer" in src
    assert "Promote best → Point Designer" in src


def test_promote_certified_search_best_clears_pd():
    from ui_nicegui.decks.control_room.certified_search import (
        promote_certified_search_x_to_point_designer,
    )
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.pd_last_outputs = {"Q_DT_eqv": 99.0}
    s.pd_last_artifact = {"outputs": {"Q_DT_eqv": 99.0}}
    s.pd_last_run_ts = 1.0
    before = float(s.inputs.get("Ip_MA", 0) or 0)
    n = promote_certified_search_x_to_point_designer(
        s, {"stage": "s1", "score": 1.0, "x": {"Ip_MA": before + 1.5}}
    )
    assert n >= 1
    assert float(s.inputs["Ip_MA"]) == before + 1.5
    assert s.pd_last_outputs is None
    assert s.pd_last_artifact is None


def test_systems_base_and_queue_invalidate_wired():
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/systems_handoff.py"
    ).read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in Path(
        "ui_nicegui/lib/systems_state_helpers.py"
    ).read_text(encoding="utf-8")
    assert "prior Point Designer KPIs cleared" in Path(
        "ui_nicegui/decks/systems_mode/base_design_ui.py"
    ).read_text(encoding="utf-8")
