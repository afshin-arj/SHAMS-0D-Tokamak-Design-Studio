"""Trade Study Studio blocking-OK screening posture ≠ L0 FEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS
from ui_nicegui.lib.trade_study_helpers import frontier_posture


def test_blocking_ok_screening_token_registered():
    assert "BLOCKING-OK SCREENING" in _NON_L0_POSTURE_TOKENS


def test_verdict_frontier_screening_not_pass_diag():
    src = Path("ui_nicegui/decks/trade_study_studio/verdict.py").read_text(encoding="utf-8")
    assert 'title_prefix="Frontier screening posture"' in src
    assert "BLOCKING-OK SCREENING" in src
    assert "blocking-OK" in src
    assert "not L0 FEASIBLE" in src
    assert "PASS+DIAG" not in src
    assert '("Feasible"' not in src
    assert "Feasibility lens" not in src
    assert "Intent-gate lens" in src


def test_labels_and_setup_blocking_ok():
    labels = Path("ui_nicegui/lib/trade_study_labels.py").read_text(encoding="utf-8")
    setup = Path("ui_nicegui/decks/trade_study_studio/setup_panel.py").read_text(encoding="utf-8")
    assert "blocking-OK" in labels
    assert "not L0 FEASIBLE" in labels
    assert "Intent-gate (blocking)" in setup
    assert "not L0 FEASIBLE" in setup


def test_controls_notify_blocking_ok():
    src = Path("ui_nicegui/decks/trade_study_studio/controls.py").read_text(encoding="utf-8")
    assert "blocking-OK" in src
    assert "not L0 FEASIBLE" in src
    assert "Run trade study (blocking-OK only)" in src


def test_explore_no_pd_green():
    src = Path("ui_nicegui/decks/trade_study_studio/explore.py").read_text(encoding="utf-8")
    assert "#2e7d32" not in src
    assert "blocking-OK" in src


def test_frontier_posture_helper():
    msg, tone = frontier_posture({"n_feasible": 0, "n_pareto": 0, "confidence": "Sparse"})
    assert "blocking-OK" in msg
    assert tone == "negative"
    msg2, tone2 = frontier_posture(
        {"n_feasible": 10, "n_pareto": 5, "confidence": "Sampling-dense"}
    )
    assert "not L0 FEASIBLE" in msg2
    assert tone2 == "info"
    helpers = Path("ui_nicegui/lib/trade_study_helpers.py").read_text(encoding="utf-8")
    assert "n_feasible" in helpers  # API key preserved


def test_nav_immediate_switch_deck_not_blocked_on_trade_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "trade_running" not in switch
    assert "ui.timer(0.06" not in switch
