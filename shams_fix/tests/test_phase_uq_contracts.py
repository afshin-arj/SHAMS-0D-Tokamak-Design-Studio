from __future__ import annotations

import pytest

try:
    from src.models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from src.phase_envelopes import PhaseSpec, run_phase_envelope_for_point
from src.uq_contracts import Interval, UncertaintyContractSpec, run_uncertainty_contract_for_point


def _base() -> PointInputs:
    # Minimal-ish PointInputs set used by UI defaults.
    return PointInputs(R0_m=1.81, a_m=0.62, kappa=1.8, Bt_T=10.0, Ip_MA=8.0, Ti_keV=10.0, fG=0.8, Paux_MW=50.0)


def test_phase_envelope_runs_and_has_worst_phase():
    base = _base()
    phases = [
        PhaseSpec(name="p1", input_overrides={"Paux_MW": 40.0}),
        PhaseSpec(name="p2", input_overrides={"Paux_MW": 60.0}),
    ]
    env = run_phase_envelope_for_point(base, phases, label_prefix="test")
    assert env["schema_version"] == "phase_envelope.v1"
    assert env["worst_phase"] in ("p1", "p2")
    assert len(env["phases_ordered"]) == 2
    assert env["envelope_verdict"] in ("PASS", "FAIL")


def test_uq_contract_runs_and_counts_corners():
    base = _base()
    spec = UncertaintyContractSpec(
        name="uq",
        intervals={
            "Paux_MW": Interval(lo=45.0, hi=55.0),
            "fG": Interval(lo=0.7, hi=0.9),
        },
    )
    con = run_uncertainty_contract_for_point(base, spec, label_prefix="test", max_dims=16)
    summ = con["summary"]
    assert summ["n_dims"] == 2
    assert summ["n_corners"] == 4
    assert summ["verdict"] in ("ROBUST_PASS", "FRAGILE", "FAIL")
