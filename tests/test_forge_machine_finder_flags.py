"""Forge Machine Finder advanced engine flag propagation."""
from __future__ import annotations

from unittest.mock import patch

from ui_nicegui.lib.forge_machine_finder_helpers import (
    load_objective_packs,
    make_evaluate_fn,
    objectives_for_pack,
    run_machine_finder,
)


def test_run_machine_finder_passes_advanced_budget_flags() -> None:
    captured: dict = {}

    def _fake_hybrid(**kwargs):
        captured.update(kwargs)
        return {"archive": [], "trace": []}

    packs = load_objective_packs("Reactor")
    pack_name = packs[0].name if packs else "Custom (manual objectives)"
    objectives = objectives_for_pack("Reactor", pack_name)

    with patch("tools.sandbox.hybrid_engine.run_hybrid_machine_finder", _fake_hybrid):
        with patch("tools.sandbox.hybrid_engine.build_archive", side_effect=lambda a, *args, **kw: a):
            run_machine_finder(
                intent="Reactor",
                anchor={"R0_m": 2.0, "Bt_T": 5.0},
                var_keys=["R0_m"],
                bounds={"R0_m": (1.8, 2.2)},
                objectives=objectives,
                pop_size=20,
                generations=5,
                surrogate_rounds=0,
                local_steps=0,
                archive_topk=10,
                enable_surface_surf=False,
                enable_skeleton=False,
                min_margin=0.05,
            )

    budgets = captured.get("budgets") or {}
    assert budgets.get("enable_surface_surf") is False
    assert budgets.get("enable_skeleton") is False
    assert budgets.get("use_knowledge_store") is False


def test_run_machine_finder_knowledge_store_flag() -> None:
    captured: dict = {}

    def _fake_hybrid(**kwargs):
        captured.update(kwargs)
        return {"archive": [], "trace": []}

    packs = load_objective_packs("Reactor")
    pack_name = packs[0].name if packs else "Custom (manual objectives)"
    objectives = objectives_for_pack("Reactor", pack_name)

    with patch("tools.sandbox.hybrid_engine.run_hybrid_machine_finder", _fake_hybrid):
        with patch("tools.sandbox.hybrid_engine.build_archive", side_effect=lambda a, *args, **kw: a):
            run_machine_finder(
                intent="Reactor",
                anchor={"R0_m": 2.0, "Bt_T": 5.0},
                var_keys=["R0_m"],
                bounds={"R0_m": (1.8, 2.2)},
                objectives=objectives,
                pop_size=20,
                generations=5,
                surrogate_rounds=0,
                local_steps=0,
                archive_topk=10,
                use_knowledge_store=True,
            )

    budgets = captured.get("budgets") or {}
    assert budgets.get("use_knowledge_store") is True


def test_make_evaluate_fn_min_margin_guard() -> None:
    packs = load_objective_packs("Reactor")
    pack_name = packs[0].name if packs else "Custom (manual objectives)"
    objectives = objectives_for_pack("Reactor", pack_name)
    fn = make_evaluate_fn("Reactor", objectives, min_margin=1.0)

    with patch(
        "ui_nicegui.lib.forge_machine_finder_helpers.evaluate_forge_candidate",
        return_value={
            "feasible": True,
            "min_signed_margin": 0.1,
            "outputs": {},
            "constraints": [],
        },
    ):
        res = fn({"R0_m": 2.0})
    assert res.get("feasible") is False
    assert res.get("failure_mode") == "min_margin_guardrail"
