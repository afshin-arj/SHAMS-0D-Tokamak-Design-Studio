"""CCFS firewall: VERIFIED never equals optimizer claims when hard constraints fail."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from constraints.bookkeeping import ConstraintSummary
from constraints.constraints import GovernanceConstraint
from extopt.certified_solve import verify_ccfs_bundle


@dataclass
class _FakeEval:
    out: Dict[str, Any]
    ok: bool = True
    message: str = ""


def _hard(name: str, *, passed: bool, severity: str = "hard") -> GovernanceConstraint:
    return GovernanceConstraint(
        name=name,
        value=2.0 if not passed else 1.0,
        limit=1.5,
        sense="<=",
        passed=passed,
        severity=severity,
        units="",
        note="test",
        group="test",
    )


def _summary(*, n_hard: int, n_hard_failed: int, feasible: bool, n_soft: int = 0) -> ConstraintSummary:
    return ConstraintSummary(
        n_total=n_hard + n_soft,
        n_hard=n_hard,
        n_soft=n_soft,
        n_hard_failed=n_hard_failed,
        worst_hard_margin_frac=(-0.2 if n_hard_failed else 0.1),
        worst_hard=("hard_fail" if n_hard_failed else None),
        soft_penalty_sum=0.05 if n_soft else 0.0,
        feasible=feasible,
    )


@pytest.fixture
def patch_ccfs(monkeypatch):
    """Wire Evaluator + constraints + summarize under test control."""

    state: Dict[str, Any] = {
        "out": {"Q": 10.0, "Pfus_total_MW": 100.0},
        "ok": True,
        "message": "",
        "cons": [_hard("beta_N", passed=True)],
        "summ": _summary(n_hard=1, n_hard_failed=0, feasible=True),
        "eval_calls": 0,
    }

    class _Ev:
        def evaluate(self, inp):
            state["eval_calls"] += 1
            state["last_inp"] = inp
            return _FakeEval(out=dict(state["out"]), ok=bool(state["ok"]), message=str(state["message"]))

    def _eval_cons(out, policy=None, **kwargs):
        state["last_policy"] = policy
        return list(state["cons"])

    def _summarize(cons, registry=None):
        return state["summ"]

    monkeypatch.setattr("extopt.certified_solve.Evaluator", _Ev)
    monkeypatch.setattr("extopt.certified_solve.evaluate_constraints", _eval_cons)
    monkeypatch.setattr("extopt.certified_solve.summarize_constraints", _summarize)

    # Bypass PointInputs validation with a lightweight stand-in.
    class _PI:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setattr("extopt.certified_solve.PointInputs", _PI)
    return state


def _bundle(claims: Dict[str, Any] | None = None, inputs: Dict[str, Any] | None = None):
    return {
        "schema_version": "ccfs_bundle.v1",
        "candidates": [
            {
                "id": "cand_0000",
                "inputs": dict(inputs or {"R0_m": 1.85, "a_m": 0.57}),
                "claims": dict(claims or {}),
            }
        ],
    }


def test_hard_fail_is_rejected_not_verified(patch_ccfs):
    patch_ccfs["cons"] = [_hard("beta_N", passed=False)]
    patch_ccfs["summ"] = _summary(n_hard=1, n_hard_failed=1, feasible=False)

    out = verify_ccfs_bundle(_bundle(claims={"status": "VERIFIED", "feasible": True, "Q": 99.0}))
    row = out["verified"][0]
    assert row["status"] == "REJECTED"
    assert row["rejection_reason"] == "hard_infeasible"
    assert row["claims_ignored"] is True
    assert row["constraints_summary"]["feasible"] is False
    assert row["constraints_summary"]["n_hard_failed"] >= 1
    assert row["claims"]["status"] == "VERIFIED"  # preserved, not trusted
    assert out["n_status_verified"] == 0
    assert out["firewall"]["claims_never_set_status"] is True
    # Independence 1.1: REJECTED rows carry no_solution_atlas.v1
    assert row["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"
    assert "verdict" in row["no_solution_atlas"]
    assert "dominant_mechanism" in row["no_solution_atlas"]


def test_claim_spoof_cannot_force_verified(patch_ccfs):
    patch_ccfs["cons"] = [_hard("fG", passed=False), _hard("q95", passed=False)]
    patch_ccfs["summ"] = _summary(n_hard=2, n_hard_failed=2, feasible=False)

    out = verify_ccfs_bundle(
        _bundle(claims={"status": "VERIFIED", "feasible": True, "objective": {"Q": 1e9}})
    )
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["status"] != out["verified"][0]["claims"].get("status")


def test_soft_only_fail_can_be_verified(patch_ccfs):
    patch_ccfs["cons"] = [
        _hard("beta_N", passed=True, severity="hard"),
        _hard("q95", passed=False, severity="soft"),
    ]
    patch_ccfs["summ"] = _summary(n_hard=1, n_hard_failed=0, feasible=True, n_soft=1)

    out = verify_ccfs_bundle(_bundle(claims={"status": "REJECTED"}))
    row = out["verified"][0]
    assert row["status"] == "VERIFIED"
    assert "rejection_reason" not in row
    assert row["constraints_summary"]["feasible"] is True


def test_happy_path_verified(patch_ccfs):
    out = verify_ccfs_bundle(_bundle())
    row = out["verified"][0]
    assert row["status"] == "VERIFIED"
    assert row["constraints_summary"]["feasible"] is True
    assert "worst_hard_margin" in row["constraints_summary"]
    assert patch_ccfs["eval_calls"] == 1
    assert out["n_status_verified"] == 1
    assert "no_solution_atlas" not in row


def test_vacuous_hard_set_fail_closed(patch_ccfs):
    patch_ccfs["cons"] = []
    patch_ccfs["summ"] = _summary(n_hard=0, n_hard_failed=0, feasible=True)

    out = verify_ccfs_bundle(_bundle(claims={"status": "VERIFIED"}))
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["rejection_reason"] == "vacuous_hard_set"
    assert out["verified"][0]["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"


def test_evaluator_not_ok_rejected(patch_ccfs):
    patch_ccfs["ok"] = False
    patch_ccfs["message"] = "boom"
    out = verify_ccfs_bundle(_bundle())
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["rejection_reason"] == "eval_error"
    assert out["verified"][0]["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"


def test_bad_inputs_rejected(patch_ccfs, monkeypatch):
    def _boom(**kwargs):
        raise TypeError("bad field")

    monkeypatch.setattr("extopt.certified_solve.PointInputs", _boom)
    out = verify_ccfs_bundle(_bundle())
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["rejection_reason"] == "eval_error"
    assert out["verified"][0]["no_solution_atlas"]["schema"] == "no_solution_atlas.v1"


def test_phase_fail_demotes_verified(patch_ccfs, monkeypatch):
    monkeypatch.setattr(
        "extopt.certified_solve._safe_bool",
        lambda x: True if x in (True, "phase_envelope") or x is True else bool(x),
    )

    # Force request path: inject phase_envelope FAIL by patching importer side via request handling.
    # Simpler: monkeypatch the phase runner modules via import path used inside verify.
    import sys
    import types

    spec_mod = types.ModuleType("phase_envelopes.spec")
    runner_mod = types.ModuleType("phase_envelopes.runner")
    pkg = types.ModuleType("phase_envelopes")
    spec_mod.default_phases_for_point = lambda inp: []
    runner_mod.run_phase_envelope_for_point = lambda *a, **k: {"envelope_verdict": "FAIL"}
    monkeypatch.setitem(sys.modules, "phase_envelopes", pkg)
    monkeypatch.setitem(sys.modules, "phase_envelopes.spec", spec_mod)
    monkeypatch.setitem(sys.modules, "phase_envelopes.runner", runner_mod)

    bundle = _bundle()
    bundle["candidates"][0]["request"] = {"phase_envelope": True}
    out = verify_ccfs_bundle(bundle)
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["rejection_reason"] == "phase_fail"


def test_phase_request_error_fail_closed(patch_ccfs, monkeypatch):
    import sys
    import types

    spec_mod = types.ModuleType("phase_envelopes.spec")
    runner_mod = types.ModuleType("phase_envelopes.runner")
    pkg = types.ModuleType("phase_envelopes")
    spec_mod.default_phases_for_point = lambda inp: []

    def _boom(*a, **k):
        raise RuntimeError("phase unavailable")

    runner_mod.run_phase_envelope_for_point = _boom
    monkeypatch.setitem(sys.modules, "phase_envelopes", pkg)
    monkeypatch.setitem(sys.modules, "phase_envelopes.spec", spec_mod)
    monkeypatch.setitem(sys.modules, "phase_envelopes.runner", runner_mod)

    bundle = _bundle()
    bundle["candidates"][0]["request"] = {"phase_envelope": True}
    out = verify_ccfs_bundle(bundle)
    assert out["verified"][0]["status"] == "REJECTED"
    assert out["verified"][0]["rejection_reason"] == "phase_error"


def test_candidate_policy_cannot_demote_hard_constraints(patch_ccfs):
    """Hostile bundles must not inject request.policy to soften the hard gate."""
    patch_ccfs["cons"] = [_hard("fG", passed=False)]
    patch_ccfs["summ"] = _summary(n_hard=1, n_hard_failed=1, feasible=False)

    bundle = _bundle(claims={"status": "VERIFIED"})
    bundle["candidates"][0]["request"] = {
        "policy": {"greenwald_enforcement": "diagnostic"},
    }
    out = verify_ccfs_bundle(bundle)
    assert patch_ccfs["last_policy"] is None
    assert out["verified"][0]["status"] == "REJECTED"


def test_integration_sparc_neighborhood_not_verified_when_hard_fails():
    """Live path: SPARC-class point must not be VERIFIED if hard-infeasible."""
    from models.inputs import PointInputs
    from constraints.constraints import evaluate_constraints
    from constraints.bookkeeping import summarize
    from evaluator.core import Evaluator

    inp = PointInputs(
        R0_m=1.85,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=8.0,
        Ti_keV=4.0,
        fG=0.8,
        Paux_MW=20.0,
    )
    res = Evaluator().evaluate(inp)
    cons = evaluate_constraints(dict(res.out or {}))
    summ = summarize(cons)
    if not summ.feasible:
        out = verify_ccfs_bundle(
            {
                "schema_version": "ccfs_bundle.v1",
                "candidates": [
                    {
                        "id": "sparc_nbhd",
                        "inputs": dict(inp.__dict__),
                        "claims": {"status": "VERIFIED", "feasible": True},
                    }
                ],
            }
        )
        assert out["verified"][0]["status"] == "REJECTED"
        assert out["verified"][0]["claims"]["status"] == "VERIFIED"
        assert out["verified"][0]["status"] != "VERIFIED"
    else:
        # If this neighborhood becomes feasible under future overlays, still assert firewall keys.
        out = verify_ccfs_bundle(
            {
                "schema_version": "ccfs_bundle.v1",
                "candidates": [{"id": "sparc_nbhd", "inputs": dict(inp.__dict__), "claims": {}}],
            }
        )
        assert out["verified"][0]["status"] in {"VERIFIED", "REJECTED"}
        assert out["firewall"]["verified_implies_hard_feasible"] is True
        if out["verified"][0]["status"] == "VERIFIED":
            assert out["verified"][0]["constraints_summary"]["feasible"] is True
            assert out["verified"][0]["constraints_summary"]["n_hard_failed"] == 0
