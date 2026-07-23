"""Compare slot handoff honesty + Mission Snapshot proxy labels (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ui_nicegui.session import DesignSession


def test_build_compare_artifact_never_holds_live_inputs_during_evaluate():
    """Critical: live session.inputs must match original while ui_evaluate runs."""
    from ui_nicegui.lib.compare_helpers import build_compare_artifact

    s = DesignSession()
    original = float(s.inputs.get("R0_m", 1.8))
    patched = original + 0.5
    seen: list[float] = []

    def _spy(inp, *, origin=""):
        seen.append(float(s.inputs.get("R0_m")))
        assert float(inp.R0_m) == patched
        return {
            "feasible": True,
            "verdict": "FEASIBLE",
            "Q_DT_eqv": 1.0,
            "hard_failures": [],
        }

    with patch("ui_nicegui.evaluate.ui_evaluate", side_effect=_spy):
        art = build_compare_artifact(s, {"R0_m": patched}, label="test-slot-B")
    assert seen and seen[0] == original
    assert float(s.inputs.get("R0_m")) == original
    assert float((art.get("inputs") or {}).get("R0_m")) == patched
    assert s.cmp_handoff_running is False


def test_compare_busy_attrs_and_deck_wiring():
    from ui_nicegui.lib.deck_busy_guard import (
        COMPARE_RUNNING_ATTRS,
        FORGE_RUNNING_ATTRS,
        PARETO_RUNNING_ATTRS,
        SUITE_RUNNING_ATTRS,
        SYSTEMS_RUNNING_ATTRS,
        TRADE_RUNNING_ATTRS,
    )

    assert "cmp_handoff_running" in COMPARE_RUNNING_ATTRS
    assert "cmp_handoff_running" in TRADE_RUNNING_ATTRS
    assert "cmp_handoff_running" in PARETO_RUNNING_ATTRS
    assert "cmp_handoff_running" in SYSTEMS_RUNNING_ATTRS
    assert "cmp_handoff_running" in SUITE_RUNNING_ATTRS
    assert "cmp_handoff_running" in FORGE_RUNNING_ATTRS
    cmp_src = Path("ui_nicegui/decks/compare/__init__.py").read_text(encoding="utf-8")
    assert "COMPARE_RUNNING_ATTRS" in cmp_src
    assert "refresh_tab_if_idle" in cmp_src
    trade = Path("ui_nicegui/decks/trade_study_studio/export_handoff.py").read_text(encoding="utf-8")
    pareto = Path("ui_nicegui/decks/pareto_lab/export_handoff.py").read_text(encoding="utf-8")
    assert "run.io_bound" in trade and "send_row_to_compare_slot" in trade
    assert "run.io_bound" in pareto and "send_row_to_compare_slot" in pareto
    assert "cmp_handoff_running" in Path("ui_nicegui/components/helm_console.py").read_text(
        encoding="utf-8"
    )


def test_regime_compass_proxy_labels_and_tbr_alias():
    from ui_nicegui.lib.pd_parity_helpers import point_summary_rows, regime_compass_rows

    rows = regime_compass_rows(
        {"beta_N": 2.1, "tbr_proxy_v403": 1.05, "q95_proxy": 3.2},
        feasible=True,
    )
    metrics = [r.get("metric") for r in rows]
    assert "βN (screening)" in metrics
    assert "βN" not in metrics
    tbr_rows = [r for r in rows if r.get("metric") == "TBR (proxy)"]
    assert tbr_rows
    assert "1.05" in str(tbr_rows[0].get("value"))

    summary = point_summary_rows({"tbr_proxy_v403": 1.12}, feasible=True)
    assert any(r["quantity"].startswith("TBR") and "1.12" in r["value"] for r in summary)


def test_helm_posture_no_raw_q_label_on_infeasible():
    src = Path("ui_nicegui/components/helm_console.py").read_text(encoding="utf-8")
    assert 'q_bit = "— (diagnostic)"' in src
    assert "cmp_handoff_running" in src
    diag = Path("ui_nicegui/decks/systems_mode/diagnostics_ui.py").read_text(encoding="utf-8")
    assert "β_N (screening)" in diag
