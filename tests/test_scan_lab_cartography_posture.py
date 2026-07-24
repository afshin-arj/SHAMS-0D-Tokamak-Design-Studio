"""Scan Lab cartography posture ≠ L0 FEASIBLE/INFEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS, verdict_banner


def test_verdict_banner_auto_prefixes_cartography_tokens():
    """Robust/Dense-slice tokens must not render as L0 'Verdict:'."""
    assert "ROBUST" in _NON_L0_POSTURE_TOKENS
    assert "DENSE SLICE" in _NON_L0_POSTURE_TOKENS
    assert "KNIFE-EDGE" in _NON_L0_POSTURE_TOKENS
    # Callable signature accepts title_prefix override
    assert callable(verdict_banner)


def test_scan_verdict_uses_cartography_posture_not_verdict_prefix():
    src = Path("ui_nicegui/decks/scan_lab/verdict.py").read_text(encoding="utf-8")
    assert 'title_prefix="Cartography posture"' in src
    assert "NOT L0 FEASIBLE" in src
    assert "Blocking-feasible fraction" in src
    # Must not call bare verdict_banner(rob) without title_prefix
    assert "verdict_banner(rob, detail=detail)" not in src


def test_scan_probe_disambiguates_neighborhood_vs_blocking():
    src = Path("ui_nicegui/decks/scan_lab/workbench.py").read_text(encoding="utf-8")
    assert "Cell neighborhood label" in src
    assert "not** L0 FEASIBLE/INFEASIBLE" in src or "not L0 FEASIBLE/INFEASIBLE" in src
    assert "PHYS-KPI-001" in src
    assert "Diagnostic residue (INFEASIBLE cell)" in src


def test_scan_busy_strip_and_idle_guards():
    init = Path("ui_nicegui/decks/scan_lab/__init__.py").read_text(encoding="utf-8")
    assert "_render_busy_strip" in init
    assert "SCAN_RUNNING_ATTRS" in init
    assert "Setup / Guided / Expert" in init
    assert "_refresh_tab_body_if_idle(session)" in init
    helm = Path("ui_nicegui/components/helm_console.py").read_text(encoding="utf-8")
    assert "SCAN_RUNNING_ATTRS" in helm
    assert "deck remount deferred until idle" in helm


def test_nav_immediate_switch_deck_not_blocked_on_busy():
    """NAV-IMMEDIATE-001: switch_deck path must not gate on scan_running."""
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "scan_running" not in switch
    assert "ui.timer(0.06" not in switch
