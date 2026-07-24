"""Control Room Certified Search L0 PASS ≠ CCFS VERIFIED (helm-decks deep loop)."""
from __future__ import annotations

from pathlib import Path

from ui_nicegui.lib.certified_opt_honesty import (
    counts_from_pass_fail_rows,
    format_pass_fail_counts,
    honesty_banner_for,
)


def test_pass_fail_counts_never_say_verified():
    line = format_pass_fail_counts(n_pass=4, n_fail=2, n_candidates=6)
    assert "L0 PASS=4" in line
    assert "FAIL=2" in line
    assert "VERIFIED=" not in line
    assert "REJECTED=" not in line
    assert "not CCFS VERIFIED" in line


def test_counts_from_rows_are_pass_fail_not_verified_kpi():
    n_pass, n_fail = counts_from_pass_fail_rows(
        [{"verdict": "PASS"}, {"verdict": "FAIL"}, {"status": "PASS"}]
    )
    assert (n_pass, n_fail) == (2, 1)


def test_certified_search_ui_uses_pass_fail_kpi():
    nice = Path("ui_nicegui/decks/control_room/certified_search.py").read_text(encoding="utf-8")
    assert "PASS_KPI_LABEL" in nice
    assert "format_pass_fail_counts" in nice
    assert "format_verified_rejected_counts" not in nice
    assert "VERIFIED / PASS-only" not in nice
    assert "L0 PASS-only ranking" in nice


def test_certified_search_honesty_negates_verified_claim():
    banner = honesty_banner_for("certified_search")
    assert "not VERIFIED" in banner or "are not VERIFIED" in banner
    assert "PASS" in banner
    assert "atlas" in banner.lower()


def test_nav_immediate_switch_deck_not_blocked_on_cr_busy():
    app = Path("ui_nicegui/app.py").read_text(encoding="utf-8")
    assert "NAV-IMMEDIATE-001" in app
    start = app.find("def _switch_deck")
    end = app.find("\ndef ", start + 1)
    switch = app[start:end]
    assert "cert_search" not in switch
    assert "ui.timer(0.06" not in switch
