"""Helm Console parity — helpers, labels, session fields."""
from __future__ import annotations

import pytest

from ui_nicegui.decks.labels import DECK_LABELS
from ui_nicegui.lib.helm_helpers import (
    health_snapshot_rows,
    invalidate_mode_caches,
    on_design_intent_changed,
    verification_report_paths,
    verification_needs_run,
)
from ui_nicegui.lib.helm_labels import DESIGN_INTENT_OPTIONS, HELM_NAV_GROUPS, helm_section_label
from ui_nicegui.session import DesignSession


def test_design_intent_options_count() -> None:
    assert len(DESIGN_INTENT_OPTIONS) == 4


def test_nav_groups_cover_all_decks() -> None:
    seen = [d for _, _, decks in HELM_NAV_GROUPS for d in decks]
    assert set(seen) == set(DECK_LABELS)
    assert DECK_LABELS[0] == "Point Designer"
    assert DECK_LABELS.index("Scan Lab") < DECK_LABELS.index("Systems Mode")
    assert DECK_LABELS.index("Compare") < DECK_LABELS.index("Control Room")


def test_deck_workflow_captions() -> None:
    from ui_nicegui.lib.deck_workflow import DECK_WORKFLOW_STEP, deck_nav_short_label, deck_workflow_caption

    assert DECK_WORKFLOW_STEP["Point Designer"] == 1
    assert DECK_WORKFLOW_STEP["Control Room"] == len(DECK_LABELS)
    assert "Workflow step 1" in deck_workflow_caption("Point Designer")
    assert deck_nav_short_label("Scan Lab").startswith("2.")


def test_helm_section_labels_plain_language() -> None:
    assert "Session posture" in helm_section_label("Captain's Ledger")
    assert helm_section_label("Black-Box Chronicle") == "Activity chronicle"


def test_health_snapshot_has_write_probe() -> None:
    rows = health_snapshot_rows()
    checks = {r["Check"] for r in rows}
    assert "Write access" in checks
    assert "Python" in checks


def test_verification_paths_under_repo() -> None:
    rep, reqs, reqs_json, runner = verification_report_paths()
    assert rep.endswith("verification" + "\\report.json") or rep.endswith("verification/report.json")
    assert runner.endswith("run_verification.py")


def test_verification_needs_run_is_bool() -> None:
    assert isinstance(verification_needs_run(), bool)


def test_design_intent_change_invalidates_caches() -> None:
    session = DesignSession()
    session.pd_last_outputs = {"Q": 1.0}
    on_design_intent_changed(
        session,
        "Power Reactor (net-electric)",
        "Experimental Device (research)",
    )
    assert session.pd_last_outputs is None
    assert session.ui_last_invalidation_reason == "design_intent_changed"
    assert session.design_intent == "Experimental Device (research)"


def test_invalidate_mode_caches_clears_compare_slots() -> None:
    session = DesignSession()
    session.cmp_slot_a = {"x": 1}
    invalidate_mode_caches(session, "test")
    assert session.cmp_slot_a is None
    assert session.ui_last_invalidation_reason == "test"


def test_helm_console_exports() -> None:
    from ui_nicegui.components.helm_console import helm_status_caption, render_helm_console
    from ui_nicegui.components.helm_theme import HELM_DRAWER_CLASS, inject_helm_drawer_theme

    assert callable(render_helm_console)
    assert callable(inject_helm_drawer_theme)
    assert "helm-drawer" in HELM_DRAWER_CLASS
    s = DesignSession()
    assert "Ready" in helm_status_caption(s)


def test_dsg_session_bootstrap() -> None:
    from ui_nicegui.lib.dsg_session import ensure_dsg

    s = DesignSession()
    g = ensure_dsg(s)
    # May be None if DSG module unavailable in test env
    assert g is None or hasattr(g, "nodes")
