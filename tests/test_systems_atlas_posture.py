"""Systems Mode micro-atlas screening posture ≠ L0 FEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS


def test_slice_tokens_are_non_l0():
    assert "DENSE SLICE" in _NON_L0_POSTURE_TOKENS
    assert "SPARSE SLICE" in _NON_L0_POSTURE_TOKENS
    assert "NEAR-EMPTY SLICE" in _NON_L0_POSTURE_TOKENS


def test_atlas_ui_uses_screening_posture_not_feasibility_map():
    src = Path("ui_nicegui/decks/systems_mode/atlas_ui.py").read_text(encoding="utf-8")
    assert 'title_prefix="Systems atlas screening posture"' in src
    assert "blocking-OK" in src
    assert "NOT Point Designer L0" in src
    assert "feasible-dominant" not in src
    assert "Feasibility map" not in src
    assert "Screening margin threshold" in src
    assert "Compute screening map" in src


def test_systems_atlas_heatmap_not_pd_green_red():
    viz = Path("ui_nicegui/lib/systems_atlas_plot.py").read_text(encoding="utf-8")
    assert "#1565c0" in viz
    assert "blocking-OK" in viz
    assert "tab20" not in viz
    assert "#2e7d32" not in viz
    assert "not PD hero" in viz or "screening" in viz


def test_systems_busy_strip_and_helm_label():
    init = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "_render_busy_strip" in init
    assert "NAV-IMMEDIATE-001" in init
    assert "SYSTEMS_RUNNING_ATTRS" in init
    helm = Path("ui_nicegui/components/helm_console.py").read_text(encoding="utf-8")
    assert "Systems Mode: Micro-atlas screening" in helm
    assert "Feasibility map" not in helm


def test_nav_immediate_switch_deck_not_blocked_on_systems_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "systems_atlas_running" not in switch
    assert "systems_solve_running" not in switch
    assert "ui.timer(0.06" not in switch
