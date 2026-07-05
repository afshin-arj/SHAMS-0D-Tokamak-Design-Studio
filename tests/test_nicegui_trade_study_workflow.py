"""Trade Study Studio NiceGUI workflow tests."""
from __future__ import annotations

from ui_nicegui.decks.trade_study_studio import ADVANCED_DECKS, render_trade_study_studio
from ui_nicegui.decks.trade_study_studio import explore, export_handoff, interpret
from ui_nicegui.lib.trade_interpret_helpers import blocking_constraints, restore_study_capsule, study_narrative
from ui_nicegui.lib.trade_study_helpers import default_objectives, objectives_catalog, run_studio_trade_study
from ui_nicegui.lib.trade_study_labels import ADVANCED_GROUPS, DECISION_TO_TAB, TRADE_TABS, normalize_trade_tab
from ui_nicegui.session import DesignSession

try:
    from src.trade_studies.spec import default_knob_sets
except ImportError:
    from trade_studies.spec import default_knob_sets  # type: ignore


def test_trade_workflow_tabs() -> None:
    assert len(TRADE_TABS) == 5
    assert normalize_trade_tab("Study Setup & Run") == "1 · Setup & Run"
    assert DECISION_TO_TAB["Explore the feasible Pareto set"] == "2 · Explore Results"


def test_advanced_groups_cover_decks() -> None:
    all_decks = [d for g in ADVANCED_GROUPS.values() for d in g]
    assert len(all_decks) == len(ADVANCED_DECKS)
    assert set(all_decks) == set(ADVANCED_DECKS)


def test_interpret_helpers_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    ksel = default_knob_sets()[0]
    objectives = default_objectives()[:2]
    _, catalog_senses = objectives_catalog()
    senses = {o: catalog_senses.get(o, "min") for o in objectives}
    rep = run_studio_trade_study(
        base,
        knob_set=ksel,
        objectives=objectives,
        objective_senses=senses,
        n_samples=20,
        seed=3,
    )
    assert isinstance(blocking_constraints(rep.get("records") or []), list)
    narrative = study_narrative(rep)
    assert "Trade study summary" in narrative
    restored = restore_study_capsule(rep)
    assert restored.get("summary")


def test_session_workflow_defaults() -> None:
    s = DesignSession()
    assert s.trade_workflow_step == "1 · Setup & Run"
    assert s.trade_teaching_mode is True
    assert callable(render_trade_study_studio)


def test_tab_renderers_import() -> None:
    assert callable(explore.render_explore_tab)
    assert callable(interpret.render_interpret_tab)
    assert callable(export_handoff.render_export_tab)
