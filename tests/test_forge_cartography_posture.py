"""Forge cartography / screening posture ≠ L0 FEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS


def test_archive_screening_is_non_l0_token():
    assert "ARCHIVE SCREENING" in _NON_L0_POSTURE_TOKENS
    assert "BLOCKING-OK SCREENING" in _NON_L0_POSTURE_TOKENS


def test_forge_dashboard_uses_screening_posture_for_workbench():
    src = Path("ui_nicegui/decks/reactor_design_forge/verdict.py").read_text(encoding="utf-8")
    assert 'title_prefix="Forge screening posture"' in src
    assert "NOT Point Designer L0" in src
    assert 'title_prefix="L0 audit"' in src
    init = Path("ui_nicegui/decks/reactor_design_forge/__init__.py").read_text(encoding="utf-8")
    assert "screening_posture" in init
    assert "ARCHIVE SCREENING" in init
    assert "audit_feasible" in init  # stripped from banner driver when wb loaded


def test_forge_cartography_heatmap_not_pd_green_red():
    viz = Path("ui_nicegui/lib/forge_viz_helpers.py").read_text(encoding="utf-8")
    assert "not PD hero verdict" in viz
    assert "Blocking-OK" in viz
    assert "#1565c0" in viz
    assert "#2e7d32" not in viz
    eng = Path("ui_nicegui/lib/forge_instrument_engine.py").read_text(encoding="utf-8")
    assert "Blocking-OK rate (MC screening)" in eng
    assert "N blocking-OK samples" in eng
    assert "not L0 FEASIBLE" in eng


def test_forge_busy_strip_and_helm_defer():
    init = Path("ui_nicegui/decks/reactor_design_forge/__init__.py").read_text(encoding="utf-8")
    assert "_render_busy_strip" in init
    assert "NAV-IMMEDIATE-001" in init
    helm = Path("ui_nicegui/components/helm_console.py").read_text(encoding="utf-8")
    assert "Reactor Design Forge" in helm
    assert "FORGE_RUNNING_ATTRS" in helm
    assert "Forge job running" in helm


def test_nav_immediate_switch_deck_not_blocked_on_forge_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "forge_mf_running" not in switch
    assert "forge_instrument_running" not in switch
    assert "ui.timer(0.06" not in switch
