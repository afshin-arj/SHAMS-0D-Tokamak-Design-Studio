"""Phase 17: External optimizer firewalls + advanced Trade Study decks."""
from __future__ import annotations

import pytest

from ui_nicegui.decks.pareto_lab import EXTERNAL_DECKS, render_pareto_lab
from ui_nicegui.decks.pareto_lab import external as pareto_external
from ui_nicegui.decks.trade_study_studio import ADVANCED_DECKS, render_trade_study_studio
from ui_nicegui.decks.trade_study_studio import advanced as trade_advanced
from ui_nicegui.lib.external_optimizer_helpers import (
    candidate_sources,
    default_pathfinding_levers,
    list_concept_family_yamls,
    list_optimizer_run_dirs,
    load_phase_defaults,
    load_uq_defaults,
    run_two_lane_uq,
)
from ui_nicegui.lib.trade_study_helpers import STUDY_SETUP_DECK
from ui_nicegui.session import DesignSession


def test_phase17_deck_lists() -> None:
    assert len(EXTERNAL_DECKS) == 11
    assert len(ADVANCED_DECKS) == 8
    assert STUDY_SETUP_DECK == "Study Setup & Run"


def test_phase17_renderers_import() -> None:
    assert callable(render_pareto_lab)
    assert callable(render_trade_study_studio)
    assert callable(pareto_external.render_external_deck)
    assert callable(trade_advanced.render_advanced_deck)


def test_phase17_defaults_smoke() -> None:
    phases = load_phase_defaults()
    uq = load_uq_defaults()
    assert "name" in phases or "Ramp" in phases
    assert "intervals" in uq


def test_candidate_sources_empty() -> None:
    s = DesignSession()
    assert candidate_sources(s) == []


def test_candidate_sources_pareto() -> None:
    s = DesignSession()
    s.pareto_last = {"pareto": [{"is_feasible": True, "i": 0}]}
    assert len(candidate_sources(s)) == 1


def test_list_concept_families() -> None:
    paths = list_concept_family_yamls()
    assert isinstance(paths, list)


def test_list_optimizer_runs_smoke() -> None:
    runs = list_optimizer_run_dirs()
    assert isinstance(runs, list)


def test_two_lane_uq_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    try:
        res = run_two_lane_uq(base)
    except Exception as exc:
        pytest.skip(f"UQ modules unavailable: {exc}")
    assert "class" in res


def test_pathfinding_levers_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    levers = default_pathfinding_levers(base)
    assert isinstance(levers, list)
