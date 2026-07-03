"""Deterministic certification regression harness (PROPOSAL-024)."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Tuple

import pytest

from models.inputs import PointInputs
from physics.hot_ion import hot_ion_point


def _base_inp() -> PointInputs:
    return PointInputs(
        R0_m=1.85,
        a_m=0.57,
        kappa=1.8,
        Bt_T=12.2,
        Ip_MA=8.7,
        Ti_keV=12.0,
        fG=0.85,
        Paux_MW=25.0,
    )


def _artifact() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    inp = _base_inp()
    out = hot_ion_point(inp)
    inp_d = inp.to_dict() if hasattr(inp, "to_dict") else dict(inp.__dict__)
    return inp_d, dict(out)


def _stable_digest(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


_CERT_CASES: List[Tuple[str, Callable[..., Dict[str, Any]], Dict[str, Any]]] = []


def _register(name: str, fn: Callable[..., Dict[str, Any]], kwargs: Dict[str, Any]) -> None:
    _CERT_CASES.append((name, fn, kwargs))


def _build_cases() -> None:
    if _CERT_CASES:
        return
    inp_d, out = _artifact()

    from certification.stability_control_certification_v374 import certify_stability_control_margins

    _register(
        "v374",
        certify_stability_control_margins,
        {"outputs": out, "inputs": inp_d, "run_id": "cert-test", "inputs_hash": "fixed"},
    )

    from certification.transport_confinement_certification_v376 import certify_transport_confinement

    _register("v376", certify_transport_confinement, {"outputs": out, "inputs": inp_d})

    from certification.structural_stress_certification_v389 import certify_structural_stress_v389

    _register("v389", certify_structural_stress_v389, {"out": out})

    from certification.robust_envelope_v352 import certify_points_under_contract

    def _stub_uq(base_inputs: PointInputs, spec: Any, **_: Any) -> Dict[str, Any]:
        return {"summary": {"verdict": "PASS", "worst_hard_margin_frac": 0.1}}

    _register(
        "v352",
        certify_points_under_contract,
        {
            "points": [_base_inp()],
            "contract_spec": {"name": "smoke", "version": "v352"},
            "run_uq_fn": _stub_uq,
        },
    )


@pytest.mark.parametrize("case_name", ["v374", "v376", "v389", "v352"])
def test_certification_deterministic_digest(case_name: str) -> None:
    _build_cases()
    match = [c for c in _CERT_CASES if c[0] == case_name]
    assert match, f"unknown certification case {case_name}"
    _, fn, kwargs = match[0]
    r1 = fn(**kwargs)
    r2 = fn(**kwargs)
    d1 = _stable_digest(r1 if isinstance(r1, dict) else {"result": str(r1)})
    d2 = _stable_digest(r2 if isinstance(r2, dict) else {"result": str(r2)})
    assert d1 == d2
    assert len(d1) == 64


def test_certification_modules_expose_certify_callable() -> None:
    from tests.test_top5_audit_fixes import _CERT_MODULES
    import importlib

    for name in _CERT_MODULES:
        mod = importlib.import_module(f"certification.{name}")
        fns = [x for x in dir(mod) if x.startswith("certify")]
        if not fns:
            # Some modules use run_* or compute_* entry points (e.g. v388).
            alt = [x for x in dir(mod) if x.startswith(("run_", "compute_", "evaluate_"))]
            assert alt, f"{name} missing certify/run/compute entry point"
