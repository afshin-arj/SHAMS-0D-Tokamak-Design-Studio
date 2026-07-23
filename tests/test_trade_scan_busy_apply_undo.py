"""Trade/Scan busy attrs + Systems Apply undo KPI clear (helm-decks loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.session import DesignSession


def test_trade_and_scan_use_shared_running_attrs():
    trade = Path("ui_nicegui/decks/trade_study_studio/__init__.py").read_text(encoding="utf-8")
    assert "TRADE_RUNNING_ATTRS" in trade
    assert 'running_attrs=("trade_running",)' not in trade
    scan = Path("ui_nicegui/decks/scan_lab/__init__.py").read_text(encoding="utf-8")
    assert "SCAN_RUNNING_ATTRS" in scan
    assert "Setup / Guided / Expert" in scan
    guard = Path("ui_nicegui/lib/deck_busy_guard.py").read_text(encoding="utf-8")
    assert "TRADE_RUNNING_ATTRS" in guard
    assert "SCAN_RUNNING_ATTRS" in guard
    assert "FORGE_RUNNING_ATTRS" in guard


def test_trade_promote_notify_clears_kpis():
    results = Path("ui_nicegui/decks/trade_study_studio/results.py").read_text(encoding="utf-8")
    export = Path("ui_nicegui/decks/trade_study_studio/export_handoff.py").read_text(encoding="utf-8")
    assert "invalidate_point_designer_after_seed" in results
    assert "prior KPIs cleared" in results
    assert "prior KPIs cleared" in export
    assert "promote_row" in export


def test_systems_apply_undo_clears_pd_kpis():
    from ui_nicegui.decks.systems_mode.apply_ui import _pop_apply_undo, _push_apply_undo

    s = DesignSession()
    s.inputs["R0_m"] = 2.0
    s.pd_last_outputs = {"Q_DT_eqv": 12.0}
    s.pd_last_artifact = {"outputs": {"Q_DT_eqv": 12.0}}
    _push_apply_undo(s)
    s.inputs["R0_m"] = 9.0
    s.pd_last_outputs = {"Q_DT_eqv": 99.0}
    assert _pop_apply_undo(s) is True
    assert float(s.inputs["R0_m"]) == 2.0
    assert s.pd_last_outputs is None
    assert s.pd_last_artifact is None


def test_pd_forge_banner_cleared_not_stale_wrong_machine():
    src = Path("ui_nicegui/decks/point_designer/__init__.py").read_text(encoding="utf-8")
    assert "prior KPIs cleared" in src
    assert "STALE until then" not in src
