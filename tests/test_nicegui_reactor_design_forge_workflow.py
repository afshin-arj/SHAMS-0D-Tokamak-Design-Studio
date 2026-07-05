"""Reactor Design Forge NiceGUI workflow — labels, instruments, tab routing."""
from __future__ import annotations

from ui_nicegui.decks.reactor_design_forge import render_reactor_design_forge
from ui_nicegui.decks.reactor_design_forge import instruments, machine_finder, workbench
from ui_nicegui.lib.forge_instrument_data import ALL_INSTRUMENTS, INSTRUMENT_GROUPS
from ui_nicegui.lib.forge_instrument_engine import compute_instrument, build_context, filter_archive
from ui_nicegui.lib.forge_interpret_helpers import scatter_axis_options, update_conflict_atlas
from ui_nicegui.lib.forge_labels import DECISION_TO_TAB, FORGE_TABS, WORKBENCH_VIEWS, normalize_forge_tab
from ui_nicegui.lib.forge_helpers import compile_forge_candidate
from ui_nicegui.lib.mode_scope_data import MODE_SCOPE
from ui_nicegui.session import DesignSession


def test_forge_workflow_tabs() -> None:
    assert len(FORGE_TABS) == 5
    assert normalize_forge_tab("Machine Finder") == "2 · Setup & Search"
    assert normalize_forge_tab("4 · Capsules & Export") == "5 · Capsules & Export"
    assert DECISION_TO_TAB["Deep-dive instruments"] == "4 · Instruments"


def test_display_labels_normalize() -> None:
    from ui_nicegui.lib.display_labels import normalize_user_label, DECK_FRONTIER_ATLAS

    assert normalize_user_label("Multi-Objective Feasible Frontier Atlas (v351)") == DECK_FRONTIER_ATLAS
    assert "(v" not in normalize_user_label("Regulatory Evidence Pack Builder (v387)")
    assert len(ALL_INSTRUMENTS) >= 60
    assert len(INSTRUMENT_GROUPS) == 9
    from ui_nicegui.lib.forge_instrument_engine import compute_instrument

    for tool in ALL_INSTRUMENTS:
        assert tool  # non-empty names


def test_workbench_views() -> None:
    assert len(WORKBENCH_VIEWS) == 7
    assert "Machine dossier (compact)" in WORKBENCH_VIEWS


def test_session_workflow_defaults() -> None:
    s = DesignSession()
    assert s.forge_workflow_step == "1 · Compile Intent"
    assert s.forge_teaching_mode is True
    assert s.forge_instrument_group == "Run intelligence"
    assert callable(render_reactor_design_forge)


def test_mode_scope_forge() -> None:
    assert "forge" in MODE_SCOPE


def test_filter_archive() -> None:
    archive = [
        {"feasible": True, "min_signed_margin": 0.1, "_score": 5.0},
        {"feasible": False, "min_signed_margin": -0.2, "_score": 1.0},
    ]
    assert len(filter_archive(archive, only_robust=True)) == 1


def test_instrument_engine_smoke() -> None:
    s = DesignSession()
    s.forge_workbench_run = {
        "intent": "Reactor",
        "archive": [{"feasible": True, "inputs": {"R0_m": 2.0}, "outputs": {"P_e_net_MW": 50}, "constraints": []}],
        "trace": [{"feasible": True, "_score": 1.0}],
    }
    ctx = build_context(s)
    v = compute_instrument("Run dashboard", ctx)
    assert v.kpis or v.json_blob is not None
    v2 = compute_instrument("Silence mode", ctx)
    assert "Silence" in v2.markdown


def test_render_modules_callable() -> None:
    assert callable(machine_finder.render_machine_finder)
    assert callable(workbench.render_forge_workbench)
    assert callable(instruments.render_instruments_tab)


def test_compile_still_works() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    result = compile_forge_candidate(base, pfus_target_mw=140.0, q_target=2.0)
    assert result.get("status") == "OK"
