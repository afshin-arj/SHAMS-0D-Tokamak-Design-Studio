"""Opt Lab certified-front screening ≠ CCFS VERIFIED (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path


def test_pareto_summary_never_maps_blocking_ok_to_verified():
    from ui_nicegui.lib.certified_front_viewer import summary_from_pareto_last

    out = summary_from_pareto_last(
        {
            "n_samples": 20,
            "feasible": [{"i": 1}, {"i": 2}, {"i": 3}],
            "pareto": [{"i": 1}],
            "summary": {"n_feasible": 3, "n_pareto": 1},
        }
    )
    assert out["n_verified"] == 0
    assert out["n_rejected"] == 0
    assert out["n_blocking_ok"] == 3
    assert "VERIFIED=" not in out["counts_line"]
    assert "blocking-OK" in out["counts_line"]
    assert out["screening_only"] is True


def test_opt_lab_entry_and_helm_guide_no_feasible_certified_front():
    entry = Path("ui_nicegui/lib/opt_lab_entry.py").read_text(encoding="utf-8")
    helm = Path("ui_nicegui/lib/helm_workflow_guide.py").read_text(encoding="utf-8")
    honesty = Path("ui_nicegui/lib/certified_opt_honesty.py").read_text(encoding="utf-8")
    assert "feasible certified front" not in entry.lower()
    assert "blocking-OK front (intent-gate)" in entry
    assert "feasible certified front" not in helm.lower()
    assert "blocking-OK" in helm
    assert "feasible set / front" not in honesty
    assert "blocking-OK (intent-gate)" in honesty


def test_chronicle_trade_kpi_blocking_ok():
    src = Path("ui_nicegui/decks/control_room/chronicle.py").read_text(encoding="utf-8")
    assert '("blocking-OK"' in src or '("blocking-OK",' in src
    # Avoid bare Feasible KPI for trade n_feasible
    assert '("Feasible", str(summary.get("n_feasible"' not in src


def test_nav_immediate_switch_deck_not_blocked_on_opt_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "opt_lab" not in switch or "opt_lab_running" not in switch
    assert "ui.timer(0.06" not in switch
