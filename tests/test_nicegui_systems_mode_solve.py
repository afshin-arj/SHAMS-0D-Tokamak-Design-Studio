"""Tests for Systems Mode solve helpers and tab labels."""

from __future__ import annotations

from ui_nicegui.lib.pd_intent_policy import hard_constraint_names_for_intent
from ui_nicegui.lib.systems_labels import normalize_systems_tab
from ui_nicegui.lib.systems_precheck import build_targets_and_variables, run_systems_precheck
from ui_nicegui.lib.systems_solve_helpers import run_systems_solve
from ui_nicegui.session import DesignSession


def test_normalize_legacy_systems_tabs() -> None:
    assert normalize_systems_tab("Diagnose") == "2 · Check & Solve"
    assert normalize_systems_tab("Compare/Apply") == "4 · Apply"
    assert normalize_systems_tab("Posture") == "5 · Review"


def test_hard_constraints_for_reactor_intent() -> None:
    hard = hard_constraint_names_for_intent("Power Reactor (net-electric)")
    assert "q95" in hard
    assert "TBR" in hard


def test_precheck_with_design_intent() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    targets, variables = build_targets_and_variables(s, base)
    report = run_systems_precheck(
        base,
        targets,
        variables,
        n_random=2,
        seed=42,
        design_intent=s.design_intent,
    )
    assert hasattr(report, "ok")


def test_systems_solve_smoke() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    targets, variables = build_targets_and_variables(s, base)
    result = run_systems_solve(
        base,
        targets,
        variables,
        max_iter=10,
        design_intent=s.design_intent,
    )
    assert isinstance(result, dict)
    assert "ok" in result
    assert isinstance(result.get("artifact"), dict)
    assert result["artifact"].get("source") == "systems_solve"
