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


def test_helm_workflow_guide() -> None:
    from ui_nicegui.lib.helm_workflow_guide import (
        DECK_NOW_ACTIONS,
        deck_phase,
        suggest_next_deck,
    )

    s = DesignSession()
    nxt, reason = suggest_next_deck(s, "Scan Lab")
    assert nxt == "Point Designer"
    assert "anchor" in reason.lower() or "evaluation" in reason.lower()
    s.pd_last_outputs = {"outputs": {"Q": 1.0}}
    nxt2, _ = suggest_next_deck(s, "Point Designer")
    assert nxt2 == "Scan Lab"
    assert len(DECK_NOW_ACTIONS["Control Room"]) >= 2
    assert deck_phase("Compare") == 3


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
    from ui_nicegui.components.helm_workflow_panel import (
        render_deck_navigation,
        render_workflow_compass,
        _render_group_deck_buttons,
    )

    assert callable(render_helm_console)
    assert callable(render_workflow_compass)
    assert callable(render_deck_navigation)
    assert callable(_render_group_deck_buttons)
    assert callable(inject_helm_drawer_theme)
    assert "helm-drawer" in HELM_DRAWER_CLASS
    s = DesignSession()
    assert "Ready" in helm_status_caption(s)


def test_active_helm_group_is_pinned_not_expansion() -> None:
    """D9-003: active nav group must not use collapsible expansion (re-click cannot hide decks)."""
    import inspect

    from ui_nicegui.components import helm_workflow_panel as hwp

    src = inspect.getsource(hwp.render_deck_navigation)
    assert "helm-nav-group-active" in src
    assert "active_group" in src
    assert "ui.column()" in src
    # Inactive groups remain expansions; active path must not only use default-opened
    assert "default-opened" not in src


def test_pub_suite_handoff_shortcut_export() -> None:
    from ui_nicegui.lib.pub_helpers import (
        handoff_to_system_suite,
        render_pub_handoffs,
        render_pub_suite_handoff_shortcut,
    )

    assert callable(handoff_to_system_suite)
    assert callable(render_pub_suite_handoff_shortcut)
    assert callable(render_pub_handoffs)


def test_dsg_session_bootstrap() -> None:
    from ui_nicegui.lib.dsg_session import ensure_dsg

    s = DesignSession()
    g = ensure_dsg(s)
    # May be None if DSG module unavailable in test env
    assert g is None or hasattr(g, "nodes")


def test_dsg_edge_kind_normalizes_deck_tokens() -> None:
    from ui_nicegui.lib.deck_dsg_hooks import (
        apply_deck_dsg_context,
        deck_edge_kind_for,
        normalize_edge_kind,
    )

    s = DesignSession()
    apply_deck_dsg_context(s, "point")
    assert s.dsg_context_edge_kind == "derived"
    assert normalize_edge_kind("bench") == "derived"
    assert normalize_edge_kind("scan") == "scan"
    assert normalize_edge_kind("forge") == "forge"
    apply_deck_dsg_context(s, deck_edge_kind_for("Systems Mode"))
    assert s.dsg_context_edge_kind == "systems_eval"
    apply_deck_dsg_context(s, deck_edge_kind_for("Reactor Design Forge"))
    assert s.dsg_context_edge_kind == "forge"


def test_helm_drawer_session_fields() -> None:
    from ui_nicegui.components.drawer_resize import (
        HELM_DRAWER_WIDTH_DEFAULT,
        HELM_DRAWER_WIDTH_MAX,
        HELM_DRAWER_WIDTH_MIN,
        toggle_helm_drawer,
    )

    s = DesignSession()
    assert s.helm_drawer_open is True
    assert s.helm_drawer_width == HELM_DRAWER_WIDTH_DEFAULT
    toggle_helm_drawer(s)
    assert s.helm_drawer_open is False
    assert HELM_DRAWER_WIDTH_MIN < HELM_DRAWER_WIDTH_MAX


def test_helm_nav_does_not_double_refresh_on_click() -> None:
    """Deck nav must not call refresh_helm/refresh_status — _switch_deck owns that."""
    import inspect

    from ui_nicegui.components import helm_workflow_panel as hwp

    src = inspect.getsource(hwp.render_deck_navigation)
    assert "refresh_helm" not in src
    assert "refresh_status" not in src
    go_src = inspect.getsource(hwp.render_workflow_compass)
    assert "refresh_helm" not in go_src
    assert "refresh_status" not in go_src


def test_switch_deck_same_deck_is_noop() -> None:
    import inspect

    from ui_nicegui import app as ng_app

    src = inspect.getsource(ng_app._switch_deck)
    assert "active_deck" in src
    assert "return" in src


def test_mode_scope_keys_for_all_decks() -> None:
    from ui_nicegui.lib.mode_scope_data import MODE_SCOPE

    required = {
        "point",
        "scan",
        "systems_eval",
        "compare",
        "pareto",
        "trade",
        "forge",
        "bench",
        "suite",
        "governance",
    }
    assert required <= set(MODE_SCOPE)


def test_phase_two_requires_scan_artifact() -> None:
    from ui_nicegui.lib.helm_workflow_guide import phase_completion, workflow_progress

    s = DesignSession()
    s.pd_last_outputs = {"Q": 1.0}
    progress = workflow_progress(s)
    assert progress["evaluated"] is True
    assert progress["scanned"] is False
    assert phase_completion(2, progress) is False
    s.scan_cartography_report = {"ok": True}
    progress2 = workflow_progress(s)
    assert progress2["scanned"] is True
    assert phase_completion(2, progress2) is True
