"""Systems Mode parity helpers — state, assistant, ranking."""

from __future__ import annotations

from ui_nicegui.lib.systems_labels import normalize_systems_tab
from ui_nicegui.lib.systems_ranking_helpers import rank_candidates
from ui_nicegui.lib.systems_state_helpers import (
    apply_proposal_to_session,
    pop_assistant_undo,
    push_assistant_undo,
    resolve_systems_problem,
)
from ui_nicegui.session import DesignSession


def test_normalize_systems_tab_legacy() -> None:
    assert normalize_systems_tab("Export") == "5 · Review"


def test_resolve_systems_problem_defaults() -> None:
    s = DesignSession()
    base, targets, variables = resolve_systems_problem(s)
    assert base is not None
    assert "Q_DT_eqv" in targets
    assert "Paux_MW" in variables


def test_rank_candidates_feasible_first() -> None:
    cands = [
        {"feasible": False, "headline": {"Q": 100}},
        {"feasible": True, "headline": {"Q": 5}},
    ]
    ranked = rank_candidates(cands, "Balanced")
    assert ranked[0]["feasible"] is True


def test_assistant_undo_stack() -> None:
    s = DesignSession()
    s.systems_targets_overrides = {}
    push_assistant_undo(s, targets={"Q_DT_eqv": 10.0}, variables={"Paux_MW": (50, 0, 200)})
    s.systems_targets_overrides = {"Q_DT_eqv": 12.0}
    assert pop_assistant_undo(s)
    assert s.systems_targets_overrides == {}


def test_apply_proposal_bounds() -> None:
    s = DesignSession()
    apply_proposal_to_session(s, {
        "description": "test",
        "changes": {"bounds": {"Paux_MW": {"lo": 0.0, "hi": 250.0}}},
    })
    assert "Paux_MW" in s.systems_bounds_overrides
