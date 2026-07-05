"""Batch 7: Reactor Design Forge Intent Compiler wiring."""
from __future__ import annotations

from ui_nicegui.decks.reactor_design_forge import render_reactor_design_forge
from ui_nicegui.lib.forge_helpers import (
    audit_candidate_inputs,
    compile_forge_candidate,
    summarize_forge_state,
)
from ui_nicegui.session import DesignSession


def test_forge_renderer_import() -> None:
    assert callable(render_reactor_design_forge)


def test_compile_forge_candidate_ok() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    result = compile_forge_candidate(base, pfus_target_mw=140.0, q_target=2.0)
    assert result.get("status") == "OK"
    cand = result.get("candidate_inputs")
    assert isinstance(cand, dict)
    assert float(cand.get("Paux_MW", 0)) == 70.0


def test_compile_forge_candidate_no_solution() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    result = compile_forge_candidate(base, pfus_target_mw=140.0, q_target=0.0)
    assert result.get("status") == "NO_SOLUTION"


def test_audit_candidate_inputs() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    compiled = compile_forge_candidate(base, pfus_target_mw=100.0, q_target=5.0)
    cand = compiled.get("candidate_inputs")
    assert isinstance(cand, dict)
    audit = audit_candidate_inputs(cand, origin="test")
    assert isinstance(audit.get("outputs"), dict)
    assert audit.get("verdict", {}).get("loaded") is True


def test_summarize_forge_state() -> None:
    s = DesignSession()
    base = s.build_point_inputs()
    compiled = compile_forge_candidate(base, pfus_target_mw=100.0, q_target=5.0)
    audit = audit_candidate_inputs(compiled["candidate_inputs"], origin="test")
    summary = summarize_forge_state(compiled, audit)
    assert summary["loaded"] is True
    assert summary["compiler_status"] == "OK"
    assert summary["audit_verdict"] in ("FEASIBLE", "INFEASIBLE")
