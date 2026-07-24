"""Pareto Lab blocking-OK screening posture ≠ L0 FEASIBLE (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS


def test_blocking_ok_screening_token_registered():
    assert "BLOCKING-OK SCREENING" in _NON_L0_POSTURE_TOKENS


def test_explore_margin_robust_not_pd_green():
    src = Path("ui_nicegui/decks/pareto_lab/explore.py").read_text(encoding="utf-8")
    assert "#1565c0" in src
    assert "#2e7d32" not in src
    assert "blocking-OK" in src
    assert "not L0 FEASIBLE" in src


def test_labels_and_verdict_not_l0_feasible():
    labels = Path("ui_nicegui/lib/pareto_labels.py").read_text(encoding="utf-8")
    verdict = Path("ui_nicegui/decks/pareto_lab/verdict.py").read_text(encoding="utf-8")
    assert "blocking-OK" in labels
    assert "not L0 FEASIBLE" in labels
    assert 'title_prefix="Frontier screening posture"' in verdict
    assert "BLOCKING-OK SCREENING" in verdict
    assert '("Feasible"' not in verdict
    assert "Feasibility lens" not in verdict
    assert "Intent-gate lens" in verdict


def test_controls_notify_blocking_ok():
    src = Path("ui_nicegui/decks/pareto_lab/controls.py").read_text(encoding="utf-8")
    assert "blocking-OK" in src
    assert "Run Pareto (blocking-OK only)" in src
    assert "not L0 FEASIBLE" in src


def test_frontier_posture_copy():
    src = Path("ui_nicegui/lib/pareto_helpers.py").read_text(encoding="utf-8")
    assert "blocking-OK" in src
    assert "No feasible designs in sampled bounds" not in src
    assert "n_feasible" in src  # API key preserved


def test_setup_language_intent_gate():
    lang = Path("ui/pareto_language.py").read_text(encoding="utf-8")
    setup = Path("ui_nicegui/decks/pareto_lab/setup_panel.py").read_text(encoding="utf-8")
    assert "blocking-OK" in lang
    assert "not L0 FEASIBLE" in lang or "not** Point Designer L0" in lang
    assert "Intent-gate (blocking)" in setup


def test_nav_immediate_switch_deck_not_blocked_on_pareto_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "pareto_running" not in switch
    assert "ui.timer(0.06" not in switch
