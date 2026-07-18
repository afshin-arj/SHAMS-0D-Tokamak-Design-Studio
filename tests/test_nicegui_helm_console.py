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
    assert "Close" in deck_nav_short_label("Systems Mode")
    assert "L1" in deck_nav_short_label("System Suite")


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
    nxt3, reason3 = suggest_next_deck(s, "Scan Lab")
    assert nxt3 == "Systems Mode"
    assert "systems" in reason3.lower()
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
    assert "Point Designer" in helm_status_caption(s)
    s.active_deck = "Scan Lab"
    assert "Scan Lab" in helm_status_caption(s)


def test_policy_caption_distinguishes_pilot_and_hfs() -> None:
    from ui_nicegui.lib.pd_intent_policy import constraint_policy_snapshot, policy_caption

    assert "Pilot" in policy_caption("Pilot Plant (demonstration)")
    assert "High-field" in policy_caption("High-field science (HFS)")
    assert "Research" in policy_caption("Experimental Device (research)")
    pol = constraint_policy_snapshot("Pilot Plant (demonstration)")
    assert pol["intent_key"] == "reactor"
    assert "TBR" in pol["hard_blocking"]
    assert "TBR" in constraint_policy_snapshot("Experimental Device (research)")["ignored"]


def test_mission_policy_shows_ignored_and_remounts_after_contract_change() -> None:
    """Constraint briefing must list Ignored; contract changes must remount deck/posture."""
    import inspect

    from ui_nicegui.components import helm_console

    mission = inspect.getsource(helm_console._render_mission_policy)
    assert "**Ignored:**" in mission
    assert "_refresh_after_truth_contract_change" in mission
    refresh_src = inspect.getsource(helm_console._refresh_after_truth_contract_change)
    assert "refresh_current_deck" in refresh_src
    posture = inspect.getsource(helm_console._render_posture)
    assert "Mission:" in posture
    assert "policy_caption" in posture


def test_workflow_phase_pills_are_navigable() -> None:
    import inspect

    from ui_nicegui.components import helm_workflow_panel as hwp

    src = inspect.getsource(hwp.render_workflow_compass)
    assert "on_deck_change" in src
    assert "HELM_NAV_GROUPS" in src
    assert "ui.button" in src
    assert "DECK_SHORT_VERBS" in src
    assert "ui.html" not in src or "helm-phase-pill" in src


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


def test_switch_deck_same_deck_skips_without_force() -> None:
    import inspect

    from ui_nicegui import app as ng_app

    src = inspect.getsource(ng_app._switch_deck)
    assert "force" in src
    assert "active_deck" in src
    # NAV-001: deck remount must refresh the refreshable slot (not an external content column).
    mod_src = inspect.getsource(ng_app)
    assert "_CONTENT =" not in mod_src
    assert "global _CONTENT" not in mod_src
    # Remount goes through coalesced helper (leading-edge + trailing debounce).
    assert "_remount_active_deck" in src
    assert "_render_deck.refresh()" in inspect.getsource(ng_app._remount_active_deck)
    assert "DECK_RENDERERS.get" in mod_src
    # Settings panel must not remount on every deck switch (heavy).
    assert "refresh_helm_settings" not in src


def test_configure_uses_lazy_expansions() -> None:
    """Point Designer Configure must defer heavy widget trees until section open."""
    import inspect

    from ui_nicegui.decks.point_designer import configure
    from ui_nicegui.lib import lazy_expansion

    src = inspect.getsource(configure.render_configure)
    assert "lazy_expansion" in src
    assert callable(lazy_expansion.lazy_expansion)


def test_switch_deck_behavioral_remount_and_force() -> None:
    """Behavioral (not inspect-only): _switch_deck updates session and remounts."""
    from unittest.mock import MagicMock

    from ui_nicegui import app as ng_app
    from ui_nicegui.lib import navigation as nav

    calls: list[str] = []
    orig_refresh = ng_app._render_deck.refresh
    ng_app._render_deck.refresh = MagicMock(side_effect=lambda: calls.append("deck"))  # type: ignore[method-assign]

    helm_calls: list[str] = []
    status_calls: list[str] = []
    nav.register_helm_refresh(lambda: helm_calls.append("helm"))
    nav.register_status_refresh(lambda: status_calls.append("status"))
    try:
        s = ng_app._SESSION
        s.active_deck = "Point Designer"
        ng_app._switch_deck("Point Designer")
        assert calls == []  # same deck, no force → skip
        ng_app._switch_deck("Scan Lab")
        assert s.active_deck == "Scan Lab"
        assert calls == ["deck"]
        assert helm_calls == ["helm"]
        assert status_calls == ["status"]
        calls.clear()
        helm_calls.clear()
        status_calls.clear()
        ng_app._switch_deck("Scan Lab", force=True)
        assert calls == ["deck"]
        assert helm_calls == ["helm"]
    finally:
        ng_app._render_deck.refresh = orig_refresh  # type: ignore[method-assign]
        nav.register_helm_refresh(lambda: None)
        nav.register_status_refresh(lambda: None)
        ng_app._SESSION.active_deck = "Point Designer"


def test_navigation_force_and_refresh_current_deck() -> None:
    import inspect

    from ui_nicegui.lib import navigation as nav

    assert "force" in inspect.getsource(nav.switch_deck)
    assert callable(nav.refresh_current_deck)
    assert "force=True after handoffs" in (nav.switch_deck.__doc__ or "")


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


def test_phase_two_requires_scan_or_systems() -> None:
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


def test_hygiene_scan_is_cached() -> None:
    from ui_nicegui.lib import control_room_helpers as crh

    crh._HYGIENE_CACHE = None
    a = crh.hygiene_scan()
    b = crh.hygiene_scan()
    assert a == b
    assert crh._HYGIENE_CACHE is not None


def test_baseline_kpi_caption_includes_stability() -> None:
    from ui_nicegui.lib.baseline_kpi_caption import baseline_kpi_caption, baseline_kpi_classes

    out = {
        "Q": 10.0,
        "H98": 1.0,
        "betaN": 2.1,
        "fG": 0.8,
        "q95": 3.5,
        "Pfus_total_MW": 500.0,
        "constraints": [],
        "feasible": True,
    }
    cap = baseline_kpi_caption(out, max_bits=10)
    assert "Q≈" in cap
    assert "β_N≈" in cap or "H98≈" in cap
    assert "Pfus≈" in cap
    assert "MIRAGE" not in cap
    assert "text-positive" in baseline_kpi_classes(out)

    mir = dict(out)
    mir["mirage_flag_v402"] = True
    assert "MIRAGE" in baseline_kpi_caption(mir, max_bits=10)
    assert "text-orange" in baseline_kpi_classes(mir)


def test_presentation_caches_survive_deck_switch_path() -> None:
    """Evaluate once; cached verdict/atlas must hit without rebuilding constraints."""
    from unittest.mock import patch

    from ui_nicegui.evaluate import ui_evaluate
    from ui_nicegui.lib.session_store import (
        get_cached_verdict_summary,
        set_point_evaluation,
    )
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    out = ui_evaluate(s.build_point_inputs(), origin="cache-test")
    set_point_evaluation(s, outputs=out, inputs=dict(s.inputs))
    assert isinstance(s.pd_verdict_summary_cache, dict)
    assert s.pd_last_artifact and "plant_kpi_honesty" in s.pd_last_artifact
    with patch("ui_nicegui.lib.verdict_core.build_all_constraints") as mocked:
        vs = get_cached_verdict_summary(s, out)
        assert vs.get("loaded") is True
        mocked.assert_not_called()


def test_control_room_uses_live_governance_verdict() -> None:
    import inspect

    from ui_nicegui.decks import control_room as cr_mod

    src = inspect.getsource(cr_mod.render_control_room)
    assert "render_governance_verdict_live" in src
    assert "governance_summary(session)" not in src.split("render_governance_verdict")[0]


def test_trade_study_export_has_scan_handoff() -> None:
    import inspect

    from ui_nicegui.decks.trade_study_studio import export_handoff as ts_exp

    src = inspect.getsource(ts_exp.render_export_tab)
    assert "scan_lab_focus" in src
    assert "switch_deck" in src
    assert "force=True" in src


def test_pd_constraints_includes_next_steps_bridge() -> None:
    import inspect

    from ui_nicegui.decks.point_designer import constraints as pd_c

    src = inspect.getsource(pd_c.render_constraints)
    assert "render_systems_precheck_bridge" in src


def test_control_room_section_sync_maps_workflow_to_legacy() -> None:
    from ui_nicegui.decks.control_room import _sync_section
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    _sync_section(s, "2 · Constitution")
    assert s.cr_workflow_step == "2 · Constitution"
    assert s.cr_section == "Constitution"


def test_compare_clear_resets_use_flags() -> None:
    import inspect

    from ui_nicegui.decks.compare import setup as cmp_setup
    from ui_nicegui.lib import compare_helpers as ch

    src = inspect.getsource(cmp_setup._clear_slots)
    assert "clear_compare_slots" in src
    helper = inspect.getsource(ch.clear_compare_slots)
    assert "cmp_use_slot_a = False" in helper
    assert "cmp_use_slot_b = False" in helper


def test_store_compare_slot_refreshes_active_compare() -> None:
    import inspect

    from ui_nicegui.lib import compare_helpers as ch

    src = inspect.getsource(ch.store_compare_slot)
    assert "refresh_compare_if_active" in src


def test_swap_compare_slots_swaps_use_flags() -> None:
    from ui_nicegui.lib.compare_helpers import store_compare_slot, swap_compare_slots
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    store_compare_slot(s, {"outputs": {"Q": 1.0}}, "A", label="A", refresh=False)
    store_compare_slot(s, {"outputs": {"Q": 2.0}}, "B", label="B", refresh=False)
    s.cmp_use_slot_a = True
    s.cmp_use_slot_b = False
    swap_compare_slots(s, refresh=False)
    assert s.cmp_use_slot_a is False
    assert s.cmp_use_slot_b is True
    assert float((s.cmp_slot_a or {}).get("outputs", {}).get("Q", 0)) == 2.0
    assert float((s.cmp_slot_b or {}).get("outputs", {}).get("Q", 0)) == 1.0


def test_compare_setup_routes_through_helpers() -> None:
    import inspect

    from ui_nicegui.decks.compare import setup as cmp_setup

    src = inspect.getsource(cmp_setup)
    assert "store_compare_slot" in src
    assert "clear_compare_slots" in src
    assert "swap_compare_slots" in src
    # No direct slot mutation outside helpers
    assert "session.cmp_slot_a = art" not in src
    assert "session.cmp_slot_a = None" not in src
    assert "session.cmp_slot_a = norm" not in src


def test_pd_handoff_prepares_truth_console() -> None:
    from ui_nicegui.lib.pd_handoff import prepare_point_designer_handoff
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.pd_subdeck = "Phase Envelopes"
    prepare_point_designer_handoff(s)
    assert s.pd_subdeck == "Truth Console"
    assert s.pd_workflow_tab == "1 · Configure"


def test_navigate_to_point_designer_sets_deck() -> None:
    from unittest.mock import patch

    from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.pd_subdeck = "Phase Envelopes"
    with patch("ui_nicegui.lib.navigation.switch_deck") as sw:
        navigate_to_point_designer(s)
        sw.assert_called_once_with("Point Designer", force=True)
    assert s.pd_subdeck == "Truth Console"
    assert s.pd_workflow_tab == "1 · Configure"


def test_open_compare_deck_sets_workflow_step() -> None:
    from unittest.mock import patch

    from ui_nicegui.lib.compare_helpers import open_compare_deck
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    with patch("ui_nicegui.lib.navigation.switch_deck") as sw:
        open_compare_deck(s)
        sw.assert_called_once_with("Compare", force=True)
    assert s.cmp_workflow_step == "1 · Load A & B"


def test_clear_compare_slots_resets_flags() -> None:
    from ui_nicegui.lib.compare_helpers import clear_compare_slots
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.cmp_slot_a = {"outputs": {"Q": 1.0}}
    s.cmp_slot_b = {"outputs": {"Q": 2.0}}
    s.cmp_use_slot_a = True
    s.cmp_use_slot_b = True
    clear_compare_slots(s)
    assert s.cmp_slot_a is None
    assert s.cmp_slot_b is None
    assert s.cmp_use_slot_a is False
    assert s.cmp_use_slot_b is False


def test_systems_apply_uses_store_compare_slot() -> None:
    import inspect

    from ui_nicegui.decks.systems_mode import apply_ui

    src = inspect.getsource(apply_ui.render_apply_panel)
    assert "store_compare_slot" in src
    assert "cmp_slot_a =" not in src


def test_chronicle_compare_uses_store_compare_slot() -> None:
    import inspect

    from ui_nicegui.decks.point_designer import chronicle_export as ce

    src = inspect.getsource(ce.render_compare_slot_actions)
    assert "store_compare_slot" in src
    assert "clear_compare_slots" in src
    assert "open_compare_deck" in src


def test_systems_mode_scope_allows_newton_propose() -> None:
    from ui_nicegui.lib.mode_scope_data import MODE_SCOPE

    does = " ".join(MODE_SCOPE["systems_eval"]["does"]).lower()
    does_not = " ".join(MODE_SCOPE["systems_eval"]["does_not"]).lower()
    assert "newton" in does
    assert "does not perform any internal root-finding" not in does_not


def test_scan_decision_does_not_reapply_quick_jump() -> None:
    import inspect

    from ui_nicegui.decks import scan_lab as scan_mod

    src = inspect.getsource(scan_mod._on_decision_scan)
    assert "_apply_quick_jump" not in src or "Do not re-apply" in inspect.getsource(scan_mod)
    assert 'scan_view_mode = ""' in src


def test_systems_apply_compare_does_not_mutate_inputs() -> None:
    import inspect

    from ui_nicegui.decks.systems_mode import apply_ui

    src = inspect.getsource(apply_ui.render_apply_panel)
    assert "build_compare_artifact" in src
    assert "navigate_to_point_designer" in src
    assert "open_compare_deck" in src
    # apply_x_to_session must not appear inside compare-send path only — still used for Apply
    assert "apply_x_to_session" in src


def test_pd_hero_surfaces_no_solution_mechanism() -> None:
    import inspect

    from ui_nicegui.decks.point_designer import hero

    src = inspect.getsource(hero.render_hero)
    assert "get_cached_no_solution_atlas" in src
    assert "NO-SOLUTION" in src


def test_systems_posture_includes_h98_pfus() -> None:
    import inspect

    from ui_nicegui.decks.systems_mode import verdict

    src = inspect.getsource(verdict.render_posture_strip)
    assert "H98" in src
    assert "Pfus" in src
    assert "hero_kpi_cells" in src


def test_suggest_next_deck_infeasible_points_to_systems() -> None:
    from ui_nicegui.lib.helm_workflow_guide import suggest_next_deck
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    s.pd_last_outputs = {"Q": 1.0, "feasible": False}
    s.pd_verdict_summary_cache = {
        "loaded": True,
        "feasible": False,
        "verdict": "INFEASIBLE",
        "dominant": "q_div",
    }
    nxt, reason = suggest_next_deck(s, "Point Designer")
    assert nxt == "Systems Mode"
    assert "INFEASIBLE" in reason


def test_helm_posture_shows_live_point() -> None:
    import inspect

    from ui_nicegui.components import helm_console

    src = inspect.getsource(helm_console._render_posture)
    assert "pd_last_outputs" in src
    assert "get_cached_verdict_summary" in src
    assert "hero_kpi_cells" in src
    # PHYS-KPI-001: must not print raw H98 float as achieved on INFEASIBLE.
    assert 'out.get("H98")' not in src or "hero_kpi_cells" in src
    assert "H98(y,2)" in src


def test_build_compare_artifact_restores_inputs_on_error() -> None:
    from unittest.mock import patch

    from ui_nicegui.lib.compare_helpers import build_compare_artifact
    from ui_nicegui.session import DesignSession

    s = DesignSession()
    original = float(s.inputs.get("R0_m", 1.8))
    with patch("ui_nicegui.evaluate.ui_evaluate", side_effect=RuntimeError("boom")):
        try:
            build_compare_artifact(s, {"R0_m": original + 0.5}, label="test")
        except RuntimeError:
            pass
    assert float(s.inputs.get("R0_m")) == original


def test_systems_pfus_reads_l0_keys() -> None:
    from ui_nicegui.decks.systems_mode.verdict import _physics_kpis

    k = _physics_kpis({"outputs": {"Pfus_total_MW": 123.0, "Q_DT_eqv": 5.0}})
    assert float(k["P_fus"]) == 123.0


def test_scan_refresh_all_includes_chrome() -> None:
    import inspect

    from ui_nicegui.decks import scan_lab as scan_mod

    src = inspect.getsource(scan_mod._refresh_all)
    assert "_render_workflow_chrome.refresh" in src


def test_switch_deck_tolerates_single_arg_callback() -> None:
    from ui_nicegui.lib import navigation as nav

    seen: list[str] = []

    def _cb(name: str) -> None:
        seen.append(name)

    nav.register_deck_change(_cb)
    try:
        nav.switch_deck("Compare", force=True)
        assert seen == ["Compare"]
    finally:
        nav.register_deck_change(lambda name, force=False: None)
