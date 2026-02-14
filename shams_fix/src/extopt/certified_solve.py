from __future__ import annotations

"""Certificate-Carrying Feasibility Solver (CCFS) interface and verifier.

This module provides a *verification* boundary between any iterative external
solver/optimizer and the frozen SHAMS truth.

Policy
------
- Any external client may propose candidate PointInputs.
- The proposal may include claims (e.g. expected feasibility, objective values).
- SHAMS *recomputes* all physics/constraints deterministically and returns a
  VERIFIED / REJECTED status, plus auditable evidence.

No part of this module changes the frozen evaluator. It only orchestrates
verification via:
  - physics.hot_ion.hot_ion_point
  - constraints.system.build_constraints_from_outputs
  - optional phase_envelopes and uncertainty contracts

Schema
------
The JSON bundle is intentionally lightweight and stable:

{
  "schema_version": "ccfs_bundle.v1",
  "candidates": [
     {
       "id": "cand_001",
       "inputs": {...PointInputs fields...},
       "claims": {"objective": {...}},
       "request": {"phase_envelope": true, "uq_contracts": true}
     }
  ]
}

Returns:
{
  "schema_version": "ccfs_verified.v1",
  "verified": [ {"id":..., "status": "VERIFIED|REJECTED", ... } ]
}
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

from physics.hot_ion import hot_ion_point
from constraints.system import build_constraints_from_outputs, summarize_constraints


def _as_point_inputs(d: Dict[str, Any]) -> PointInputs:
    if not isinstance(d, dict):
        raise TypeError("inputs must be an object")
    return PointInputs(**d)  # dataclass validates field names


def _safe_bool(x: Any) -> bool:
    return bool(x) if x is not None else False


def verify_ccfs_bundle(bundle: Dict[str, Any], *, default_request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verify a CCFS candidate bundle against frozen truth."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if str(bundle.get("schema_version", "")) not in {"ccfs_bundle.v1", "ccfs_bundle"}:
        # accept legacy alias
        pass

    cands = bundle.get("candidates")
    if not isinstance(cands, list) or not cands:
        raise ValueError("bundle.candidates must be a non-empty list")

    default_request = dict(default_request or {})

    verified: List[Dict[str, Any]] = []

    for i, c in enumerate(cands):
        cid = None
        try:
            cid = str(c.get("id", f"cand_{i:04d}"))
            inp = _as_point_inputs(dict(c.get("inputs") or {}))

            out = hot_ion_point(inp)
            cons = build_constraints_from_outputs(out)
            summ = summarize_constraints(cons).to_dict()

            # Optional worst-phase / worst-corner verification (requestable).
            req = dict(default_request)
            if isinstance(c.get("request"), dict):
                req.update(dict(c.get("request")))

            phase_env = None
            if _safe_bool(req.get("phase_envelope")):
                try:
                    from phase_envelopes.spec import default_phases_for_point
                    from phase_envelopes.runner import run_phase_envelope_for_point
                    phases = default_phases_for_point(inp)
                    phase_env = run_phase_envelope_for_point(inp, phases, label_prefix=f"ccfs:{cid}")
                except Exception as e:
                    phase_env = {"error": f"phase_envelope_failed: {e}"}

            uq = None
            if _safe_bool(req.get("uq_contracts")):
                try:
                    from uq_contracts.spec import default_uncertainty_contract
                    from uq_contracts.runner import run_uncertainty_contract_for_point
                    spec = default_uncertainty_contract(inp)
                    uq = run_uncertainty_contract_for_point(inp, spec, label_prefix=f"ccfs:{cid}")
                except Exception as e:
                    uq = {"error": f"uq_contracts_failed: {e}"}

            # Verification decision.
            feasible_nominal = bool(summ.get("feasible", False))
            status = "VERIFIED" if feasible_nominal else "REJECTED"

            # If worst-case checks requested, require their success.
            if status == "VERIFIED":
                if isinstance(phase_env, dict) and phase_env.get("envelope_verdict") == "FAIL":
                    status = "REJECTED"
                try:
                    if isinstance(uq, dict) and ((uq.get("summary") or {}).get("verdict") == "FAIL"):
                        status = "REJECTED"
                except Exception:
                    pass

            verified.append({
                "id": cid,
                "status": status,
                "inputs": dict(inp.__dict__),
                "outputs": dict(out),
                "constraints_summary": summ,
                "constraints": [getattr(x, "to_dict", lambda: dict(x.__dict__))() for x in cons],
                "phase_envelope": phase_env,
                "uq_contracts": uq,
                "claims": dict(c.get("claims") or {}),
            })

        except Exception as e:
            verified.append({
                "id": str(cid or f"cand_{i:04d}"),
                "status": "REJECTED",
                "error": f"verification_failed: {e}",
            })

    return {
        "schema_version": "ccfs_verified.v1",
        "n_candidates": int(len(cands)),
        "verified": verified,
    }
