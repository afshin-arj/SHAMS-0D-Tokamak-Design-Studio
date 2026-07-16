from __future__ import annotations

"""Certificate-Carrying Feasibility Solver (CCFS) interface and verifier.

This module provides a *verification* boundary between any iterative external
solver/optimizer and the frozen SHAMS truth.

Policy
------
- Any external client may propose candidate PointInputs.
- The proposal may include claims (e.g. expected feasibility, objective values).
- Claims never influence VERIFIED / REJECTED — SHAMS recomputes physics and
  governance hard constraints deterministically.
- VERIFIED requires: Evaluator re-eval + zero hard-constraint failures
  (optional phase/UQ envelopes must not FAIL when requested).
- Soft / diagnostic failures do not block VERIFIED.

No part of this module changes the frozen evaluator. It only orchestrates
verification via:
  - evaluator.core.Evaluator.evaluate  (single choke point)
  - constraints.constraints.evaluate_constraints
  - constraints.bookkeeping.summarize  (feasible <=> n_hard_failed == 0)
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

from typing import Any, Dict, List, Optional

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    from models.inputs import PointInputs  # type: ignore

try:
    from ..evaluator.core import Evaluator  # type: ignore
except Exception:
    from evaluator.core import Evaluator  # type: ignore

from constraints.constraints import evaluate_constraints
from constraints.bookkeeping import summarize as summarize_constraints


def _as_point_inputs(d: Dict[str, Any]) -> PointInputs:
    if not isinstance(d, dict):
        raise TypeError("inputs must be an object")
    return PointInputs(**d)  # dataclass validates field names


def _safe_bool(x: Any) -> bool:
    return bool(x) if x is not None else False


def _constraint_row(c: Any) -> Dict[str, Any]:
    if hasattr(c, "as_dict"):
        return dict(c.as_dict())
    if hasattr(c, "to_dict"):
        return dict(c.to_dict())
    return dict(getattr(c, "__dict__", {}) or {})


def _empty_atlas(*, verdict: str = "UNKNOWN") -> Dict[str, Any]:
    return {
        "schema": "no_solution_atlas.v1",
        "verdict": verdict,
        "dominant_constraint": "",
        "dominant_mechanism": "GENERAL",
        "mechanism_map": {},
        "hard_failures": [],
        "n_hard_failures": 0,
        "parity_aligned": True,
    }


def _atlas_for_outputs(out: Optional[Dict[str, Any]], *, design_intent: Optional[str] = None) -> Dict[str, Any]:
    """Attach no_solution_atlas.v1 on REJECTED / infeasible CCFS rows."""
    if not isinstance(out, dict) or not out:
        return _empty_atlas(verdict="UNKNOWN")
    try:
        try:
            from diagnostics.no_solution_atlas import build_no_solution_atlas  # type: ignore
        except ImportError:
            from src.diagnostics.no_solution_atlas import build_no_solution_atlas  # type: ignore
        return build_no_solution_atlas(out, design_intent=design_intent)
    except Exception:
        atlas = _empty_atlas(verdict="UNKNOWN")
        atlas["atlas_build_error"] = True
        return atlas


def _decision_status(
    *,
    feasible_hard: bool,
    phase_env: Any,
    uq: Any,
    phase_requested: bool = False,
    uq_requested: bool = False,
) -> tuple[str, str]:
    """Return (status, rejection_reason). Claims must never call this."""
    if not feasible_hard:
        return "REJECTED", "hard_infeasible"
    if phase_requested and isinstance(phase_env, dict):
        if phase_env.get("envelope_verdict") == "FAIL":
            return "REJECTED", "phase_fail"
        if phase_env.get("error"):
            return "REJECTED", "phase_error"
    if uq_requested and isinstance(uq, dict):
        try:
            if (uq.get("summary") or {}).get("verdict") == "FAIL":
                return "REJECTED", "uq_fail"
        except Exception:
            pass
        if uq.get("error"):
            return "REJECTED", "uq_error"
    return "VERIFIED", ""


def verify_ccfs_bundle(bundle: Dict[str, Any], *, default_request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Verify a CCFS candidate bundle against frozen truth.

    Firewall invariants
    -------------------
    - External claims never set status.
    - VERIFIED implies hard-feasible under governance constraints
      (`constraints_summary.feasible is True` and `n_hard_failed == 0`).
    - Soft-only failures may still be VERIFIED.
    """
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if str(bundle.get("schema_version", "")) not in {"ccfs_bundle.v1", "ccfs_bundle"}:
        # accept legacy alias
        pass

    cands = bundle.get("candidates")
    if not isinstance(cands, list) or not cands:
        raise ValueError("bundle.candidates must be a non-empty list")

    default_request = dict(default_request or {})
    evaluator = Evaluator()

    verified: List[Dict[str, Any]] = []

    for i, c in enumerate(cands):
        cid = None
        try:
            if not isinstance(c, dict):
                raise TypeError("each candidate must be an object")
            cid = str(c.get("id", f"cand_{i:04d}"))
            claims = dict(c.get("claims") or {})
            inp = _as_point_inputs(dict(c.get("inputs") or {}))

            # Frozen choke point — never trust claims or kit outputs for status.
            res = evaluator.evaluate(inp)
            out = dict(getattr(res, "out", None) or {})
            if not bool(getattr(res, "ok", True)):
                verified.append({
                    "id": cid,
                    "status": "REJECTED",
                    "rejection_reason": "eval_error",
                    "claims_ignored": True,
                    "claims": claims,
                    "error": f"evaluator_not_ok: {getattr(res, 'message', '')}",
                    "no_solution_atlas": _atlas_for_outputs(out if isinstance(out, dict) else None),
                })
                continue

            # Policy may demote q95/fG hard→soft. Only trusted default_request.policy
            # is allowed — never per-candidate request.policy (hostile-bundle risk).
            policy = None
            if isinstance(default_request.get("policy"), dict):
                policy = dict(default_request["policy"])

            cons = evaluate_constraints(out, policy=policy)
            summ = summarize_constraints(cons).to_dict()
            # Orchestrator alias (historical key name).
            if "worst_hard_margin" not in summ and summ.get("worst_hard_margin_frac") is not None:
                summ["worst_hard_margin"] = summ.get("worst_hard_margin_frac")

            req = dict(default_request)
            if isinstance(c.get("request"), dict):
                req.update({k: v for k, v in dict(c.get("request")).items() if k != "policy"})

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

            feasible_hard = bool(summ.get("feasible", False)) and int(summ.get("n_hard_failed", 1) or 0) == 0
            vacuous = int(summ.get("n_hard", 0) or 0) == 0
            # Vacuous: no hard constraints evaluated → not VERIFIED (fail closed).
            if vacuous:
                feasible_hard = False
                if summ.get("feasible") is True:
                    summ = dict(summ)
                    summ["feasible"] = False
                    summ["vacuous_hard_set"] = True

            status, rejection_reason = _decision_status(
                feasible_hard=feasible_hard,
                phase_env=phase_env,
                uq=uq,
                phase_requested=_safe_bool(req.get("phase_envelope")),
                uq_requested=_safe_bool(req.get("uq_contracts")),
            )
            if status != "VERIFIED" and vacuous and rejection_reason == "hard_infeasible":
                rejection_reason = "vacuous_hard_set"

            row: Dict[str, Any] = {
                "id": cid,
                "status": status,
                "claims_ignored": True,
                "inputs": dict(inp.__dict__),
                "outputs": out,
                "constraints_summary": summ,
                "constraints": [_constraint_row(x) for x in cons],
                "phase_envelope": phase_env,
                "uq_contracts": uq,
                "claims": claims,
            }
            if status != "VERIFIED":
                row["rejection_reason"] = rejection_reason or "hard_infeasible"
                # Independence ticket 1.1: REJECTED rows always carry atlas.
                _intent = getattr(inp, "design_intent", None) or (inp.__dict__ or {}).get("design_intent")
                atlas = _atlas_for_outputs(
                    out,
                    design_intent=str(_intent) if _intent else None,
                )
                # Hard-infeasible gate: never advertise FEASIBLE atlas on hard reject.
                if rejection_reason in {"hard_infeasible", "vacuous_hard_set"} and str(atlas.get("verdict")) == "FEASIBLE":
                    atlas = dict(atlas)
                    atlas["verdict"] = "INFEASIBLE"
                    atlas["atlas_aligned_to_rejection"] = True
                atlas = dict(atlas)
                atlas["rejection_reason"] = rejection_reason or "hard_infeasible"
                row["no_solution_atlas"] = atlas
            verified.append(row)

        except Exception as e:
            verified.append({
                "id": str(cid or f"cand_{i:04d}"),
                "status": "REJECTED",
                "rejection_reason": "eval_error",
                "claims_ignored": True,
                "error": f"verification_failed: {e}",
                "no_solution_atlas": _empty_atlas(verdict="UNKNOWN"),
            })

    n_verified = sum(1 for v in verified if str(v.get("status")) == "VERIFIED")
    n_rejected = int(len(verified) - n_verified)

    return {
        "schema_version": "ccfs_verified.v1",
        "n_candidates": int(len(cands)),
        "n_status_verified": int(n_verified),
        "n_status_rejected": int(n_rejected),
        "firewall": {
            "claims_never_set_status": True,
            "verified_implies_hard_feasible": True,
            "evaluator_choke_point": "Evaluator.evaluate",
        },
        "verified": verified,
    }
