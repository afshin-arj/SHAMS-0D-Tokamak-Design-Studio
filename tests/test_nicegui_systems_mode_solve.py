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
    assert "target_converged" in result
    assert "intent_feasible" in result
    assert isinstance(result.get("artifact"), dict)
    assert result["artifact"].get("source") == "systems_solve"
    rs = result["artifact"].get("run_summary")
    if rs is not None:
        assert isinstance(rs, dict)
        assert "tightest_hard_constraints" in rs


def test_systems_solve_multistart_fallback() -> None:
    """Regression: multistart ladder must not pass unsupported cache kwargs."""
    from ui_nicegui.lib.helm_helpers import apply_legacy_reference_machine_to_session

    s = DesignSession()
    apply_legacy_reference_machine_to_session(s, "SPARC-class (compact HTS)")
    s.systems_use_q = True
    s.systems_q_target = 2.0
    s.systems_use_h = True
    s.systems_h_target = 1.15
    s.systems_solve_ip = True
    s.systems_solve_fg = True
    base = s.build_point_inputs()
    targets, variables = build_targets_and_variables(s, base)
    result = run_systems_solve(
        base,
        targets,
        variables,
        max_iter=20,
        design_intent=s.design_intent,
    )
    assert isinstance(result, dict)
    assert "target_converged" in result


def test_systems_target_rows_after_solve() -> None:
    from ui_nicegui.lib.systems_target_banner import systems_target_rows

    s = DesignSession()
    s.systems_use_q = True
    s.systems_q_target = 10.0
    rows = systems_target_rows(s, {"Q_DT_eqv": 9.5, "H98": 1.1}, feasible=True)
    assert rows
    assert rows[0]["quantity"] == "Q_DT_eqv"
    assert rows[0]["status"] in ("ok", "miss", "n/a")


def test_systems_target_rows_infeasible_never_ok() -> None:
    from ui_nicegui.lib.systems_target_banner import systems_target_rows

    s = DesignSession()
    s.systems_use_q = True
    s.systems_q_target = 10.0
    # Value meets the ≥ floor numerically, but intent is infeasible.
    rows = systems_target_rows(s, {"Q_DT_eqv": 12.0}, feasible=False)
    assert rows
    assert rows[0]["status"] == "diag"
    assert "ok" not in {r["status"] for r in rows}


def test_validate_systems_problem_dimension() -> None:
    from ui_nicegui.lib.systems_state_helpers import validate_systems_problem

    ok, _ = validate_systems_problem({"Q_DT_eqv": 10.0, "H98": 1.1}, {"Paux_MW": (50, 0, 200)})
    assert not ok
    ok2, _ = validate_systems_problem(
        {"Q_DT_eqv": 10.0},
        {"Paux_MW": (50, 0, 200)},
    )
    assert ok2


def test_fg_bounds_cap() -> None:
    from types import SimpleNamespace

    from ui_nicegui.lib.systems_precheck import build_targets_and_variables

    s = DesignSession()
    s.systems_solve_fg = True
    _, variables = build_targets_and_variables(s, SimpleNamespace(Ip_MA=8, fG=0.8, Paux_MW=50))
    assert variables["fG"][2] <= 1.0


def test_collect_candidates_includes_target_solve() -> None:
    from ui_nicegui.lib.systems_workflow_helpers import collect_candidates

    s = DesignSession()
    base = s.build_point_inputs()
    s.systems_last_solve_result = {
        "ok": True,
        "target_converged": True,
        "intent_feasible": True,
        "inp": base,
        "out": {"Q_DT_eqv": 9.5, "H98": 1.0},
    }
    cands = collect_candidates(s)
    assert any(c["id"] == "target_solve" for c in cands)


def test_decision_to_tab_mapping() -> None:
    from ui_nicegui.lib.systems_labels import DECISION_STATES, DECISION_TO_TAB

    assert DECISION_TO_TAB[DECISION_STATES[0]] == "2 · Check & Solve"
    assert DECISION_TO_TAB[DECISION_STATES[4]] == "4 · Apply"


def test_systems_teaching_mode_default_on() -> None:
    s = DesignSession()
    assert s.systems_teaching_mode is True


def test_evaluator_residuals_min_sense() -> None:
    try:
        from src.evaluator.core import Evaluator
    except ImportError:
        from evaluator.core import Evaluator  # type: ignore

    out = {"Q_DT_eqv": 12.0, "H98": 1.2}
    targets = {"Q_DT_eqv": 10.0, "H98": 1.0}
    eq = Evaluator.residuals(out, targets)
    assert eq["Q_DT_eqv"] == 2.0
    mn = Evaluator.residuals(out, targets, senses={"Q_DT_eqv": "min", "H98": "min"})
    assert mn["Q_DT_eqv"] == 0.0
    assert mn["H98"] == 0.0
    below = Evaluator.residuals({"Q_DT_eqv": 8.0}, {"Q_DT_eqv": 10.0}, senses={"Q_DT_eqv": "min"})
    assert below["Q_DT_eqv"] == 2.0


def test_pfus_target_build() -> None:
    from types import SimpleNamespace

    s = DesignSession()
    s.systems_use_q = False
    s.systems_use_pfus = True
    s.systems_pfus_target = 150.0
    s.systems_solve_paux = True
    targets, variables = build_targets_and_variables(s, SimpleNamespace(Ip_MA=8, fG=0.8, Paux_MW=50))
    assert "Pfus_DT_adj_MW" in targets
    assert "Paux_MW" in variables


def test_assumption_lock_drift_blocks() -> None:
    from ui_nicegui.lib.systems_assumption_lock import assumption_settings_hash, check_assumption_lock

    s = DesignSession()
    s.systems_assumption_lock_enabled = True
    s.systems_assumption_lock_hash = assumption_settings_hash(s)
    ok, _ = check_assumption_lock(s)
    assert ok
    s.systems_q_target = 99.0
    ok2, msg2 = check_assumption_lock(s)
    assert not ok2
    assert msg2


def test_fs_objective_negated_tbr() -> None:
    from ui_nicegui.lib.systems_fs_helpers import fs_objective_value

    v = fs_objective_value({"TBR": 1.1}, "-TBR")
    assert v == -1.1


def test_systems_transport_overlay_flags() -> None:
    from ui_nicegui.decks.systems_mode.setup import _TRANSPORT_OVERLAY_FLAGS

    assert "include_transport_contracts_v371" in _TRANSPORT_OVERLAY_FLAGS
    assert "include_transport_envelope_v396" in _TRANSPORT_OVERLAY_FLAGS
    assert "include_profile_proxy_v397" in _TRANSPORT_OVERLAY_FLAGS
