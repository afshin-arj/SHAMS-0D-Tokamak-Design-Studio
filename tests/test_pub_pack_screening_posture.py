"""Pub Lab pack screening posture ≠ L0 Verdict: PASS (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.components.verdict_banner import _NON_L0_POSTURE_TOKENS


def test_blocking_ok_screening_token_registered():
    assert "BLOCKING-OK SCREENING" in _NON_L0_POSTURE_TOKENS


def test_pack_verdict_strip_no_pack_prefix_strip():
    src = Path("ui_nicegui/lib/pub_helpers.py").read_text(encoding="utf-8")
    assert '.replace("PACK ", "")' not in src
    assert 'title_prefix="Pack screening posture"' in src
    assert "BLOCKING-OK SCREENING" in src
    assert "NOT Point Designer L0" in src
    assert 'verdict_banner("PASS"' not in src


def test_pack_summary_posture_strings_unchanged():
    from ui_nicegui.lib.pub_helpers import pack_summary_from_outdir

    # Empty / missing → not loaded
    assert pack_summary_from_outdir(None).get("loaded") is False
    assert pack_summary_from_outdir("").get("loaded") is False


def test_pack_status_chrome_not_always_positive():
    init = Path("ui_nicegui/decks/publication_benchmarks/__init__.py").read_text(encoding="utf-8")
    assert "Pack ready:" not in init or "pack_summary_from_outdir" in init
    assert "pack_summary_from_outdir" in init
    assert "PACK PASS" in init or "PACK MIXED" in init


def test_orientation_q95_proxy_and_screening():
    ori = Path("ui_nicegui/decks/publication_benchmarks/orientation.py").read_text(encoding="utf-8")
    assert "q95_proxy" in ori
    assert "not L0 FEASIBLE" in ori or "screening" in ori.lower()


def test_nav_immediate_switch_deck_not_blocked_on_pub_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "pub_bench_running" not in switch
    assert "pub_running" not in switch
    assert "pub_atlas_running" not in switch
    assert "ui.timer(0.06" not in switch
