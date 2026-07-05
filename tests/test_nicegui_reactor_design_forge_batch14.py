"""Phase 14: Reactor Design Forge Machine Finder + Capsules."""
from __future__ import annotations

import pytest

from ui_nicegui.decks.reactor_design_forge import capsules, machine_finder
from ui_nicegui.lib.forge_machine_finder_helpers import (
    anchor_from_session,
    archive_table_rows,
    compute_bounds,
    evaluate_forge_candidate,
    intent_from_label,
    objectives_for_pack,
    restore_workbench_from_capsule,
    run_machine_finder,
    summarize_workbench_run,
)
from ui_nicegui.session import DesignSession


def test_machine_finder_renderer_import() -> None:
    assert callable(machine_finder.render_machine_finder)
    assert callable(capsules.render_capsules)


def test_intent_from_label() -> None:
    assert intent_from_label("Power Reactor (net-electric)") == "Reactor"
    assert intent_from_label("Experimental Device (research)") == "Research"


def test_compute_bounds() -> None:
    anchor = {"R0_m": 6.0, "Bt_T": 5.0}
    b = compute_bounds(anchor, ["R0_m", "Bt_T"], bound_mode="Medium (±20%)")
    assert b["R0_m"][0] < 6.0 < b["R0_m"][1]


def test_evaluate_forge_candidate_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    inp = anchor_from_session(base)
    res = evaluate_forge_candidate(inp, "Reactor", origin="test")
    assert isinstance(res.get("outputs"), dict)
    assert "feasible" in res


def test_run_machine_finder_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    anchor = anchor_from_session(base)
    var_keys = ["R0_m", "Paux_MW"]
    bounds = compute_bounds(anchor, var_keys, bound_mode="Tight (±10%)")
    packs = __import__(
        "tools.sandbox.optimizer_engines", fromlist=["default_objective_packs"]
    ).default_objective_packs("Reactor")
    Objective = __import__("tools.sandbox.hybrid_engine", fromlist=["Objective"]).Objective
    objectives = [Objective(**o.__dict__) for o in packs[0].objectives]
    run_rep = run_machine_finder(
        intent="Reactor",
        anchor=anchor,
        var_keys=var_keys,
        bounds=bounds,
        objectives=objectives,
        pop_size=20,
        generations=5,
        surrogate_rounds=2,
        local_steps=10,
        archive_topk=20,
        require_feasible_only=False,
    )
    assert isinstance(run_rep, dict)
    assert run_rep.get("archive") is not None
    summary = summarize_workbench_run(run_rep)
    assert summary["loaded"] is True
    rows = archive_table_rows(run_rep, limit=5)
    assert isinstance(rows, list)


def test_restore_workbench_from_capsule() -> None:
    capsule = {
        "schema": "shams.opt_sandbox.run_capsule.v2",
        "intent": "Reactor",
        "archive": [],
        "trace": [],
        "lens": {"objectives": []},
    }
    run_rep = restore_workbench_from_capsule(capsule)
    assert run_rep.get("kind") == "optimization_sandbox_hybrid_run_replay"
    assert run_rep.get("intent") == "Reactor"


def test_capsule_diff_smoke() -> None:
    from ui_nicegui.lib.forge_machine_finder_helpers import diff_capsule_json

    a = {
        "schema": "shams.opt_sandbox.run_capsule.v2",
        "run_id": "a",
        "intent": "Reactor",
        "archive": [{"x": 1}],
        "trace": [],
    }
    b = {
        "schema": "shams.opt_sandbox.run_capsule.v2",
        "run_id": "b",
        "intent": "Reactor",
        "archive": [{"x": 2}],
        "trace": [],
    }
    try:
        d = diff_capsule_json(a, b)
    except RuntimeError:
        pytest.skip("diff_capsules unavailable")
    assert isinstance(d, dict)
