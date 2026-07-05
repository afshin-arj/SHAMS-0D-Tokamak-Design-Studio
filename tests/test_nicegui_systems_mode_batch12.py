"""Phase 12: Systems Mode recovery, search, apply, export."""
from __future__ import annotations

from ui_nicegui.lib.systems_precheck import build_targets_and_variables
from ui_nicegui.lib.systems_workflow_helpers import (
    apply_x_to_session,
    collect_candidates,
    recovery_seed,
    run_feasible_search,
    run_seeded_recovery,
    systems_export_bytes,
    tuple_bounds_to_dict,
)
from ui_nicegui.session import DesignSession


def test_tuple_bounds_to_dict() -> None:
    d = tuple_bounds_to_dict({"Paux_MW": (50.0, 0.0, 200.0)})
    assert d["Paux_MW"]["lo"] == 0.0
    assert d["Paux_MW"]["hi"] == 200.0


def test_recovery_seed_from_inputs() -> None:
    s = DesignSession()
    _, variables = build_targets_and_variables(s, s.build_point_inputs())
    seed = recovery_seed(s, variables)
    assert "Paux_MW" in seed


def test_seeded_recovery_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    _, variables = build_targets_and_variables(s, base)
    rep = run_seeded_recovery(
        base,
        variables,
        budget_evals=40,
        local_steps=15,
        multi_start=5,
        rng_seed=1,
    )
    assert isinstance(rep, dict)
    assert "ok" in rep
    assert "best_point" in rep


def test_feasible_search_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    _, variables = build_targets_and_variables(s, base)
    rep = run_feasible_search(
        base,
        variables,
        budget=25,
        topk=3,
        rng_seed=2,
    )
    assert isinstance(rep, dict)
    assert "candidates" in rep


def test_apply_x_to_session() -> None:
    s = DesignSession()
    before = float(s.inputs["Paux_MW"])
    apply_x_to_session(s, {"Paux_MW": before + 5.0})
    assert float(s.inputs["Paux_MW"]) == before + 5.0


def test_collect_candidates_after_recovery() -> None:
    s = DesignSession()
    s.systems_recovery_last = {
        "ok": True,
        "reason": "test",
        "best_point": {"Paux_MW": 55.0},
    }
    cands = collect_candidates(s)
    assert len(cands) == 1
    assert cands[0]["source"] == "Seeded Recovery"


def test_systems_export_bytes() -> None:
    s = DesignSession()
    s.systems_run_cards = [{"kind": "test"}]
    data = systems_export_bytes(s)
    assert b"systems_run_cards" in data
