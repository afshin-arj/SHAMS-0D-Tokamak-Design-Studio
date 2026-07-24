"""Systems Mode precheck/explore/frontier screening ≠ L0 FEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path


def test_precheck_status_uses_blocking_ok_screening():
    src = Path("ui_nicegui/decks/systems_mode/precheck_ui.py").read_text(encoding="utf-8")
    assert "blocking-OK within bounds (screening)" in src
    assert "NOT Point Designer L0 Verdict" in src
    assert "Precheck feasible" not in src
    assert "✓ feasible within bounds" not in src
    assert 'type="positive" if _precheck_ok' not in src


def test_explore_trace_not_pd_green_feasible():
    src = Path("ui_nicegui/decks/systems_mode/explore_ui.py").read_text(encoding="utf-8")
    assert "#1565c0" in src
    assert "#2e7d32" not in src
    assert "blocking-OK (intent)" in src
    assert 'name="Feasible"' not in src
    assert "not PD hero" in src
    assert "Intent-gated design search" in src


def test_frontier_legend_blocking_ok_not_l0():
    src = Path("ui_nicegui/decks/systems_mode/frontier_ui.py").read_text(encoding="utf-8")
    assert "blocking-OK" in src
    assert "hard-fail" in src
    assert "not L0 FEASIBLE" in src
    assert 'name="Feasible"' not in src
    assert 'name="Infeasible"' not in src


def test_systems_workflow_chips_blocking_ok():
    src = Path("ui_nicegui/decks/systems_mode/__init__.py").read_text(encoding="utf-8")
    assert "blocking-OK" in src
    assert "({n_feas} feasible)" not in src
    assert "Nearest blocking-OK point" in src
    assert "Budgeted blocking-OK search" in src


def test_nav_immediate_switch_deck_not_blocked_on_systems_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "systems_atlas_running" not in switch
    assert "systems_precheck_running" not in switch
    assert "systems_fs_running" not in switch
    assert "ui.timer(0.06" not in switch
