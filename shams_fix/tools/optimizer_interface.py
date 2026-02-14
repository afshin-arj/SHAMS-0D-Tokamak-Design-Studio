from __future__ import annotations
"""External Optimizer Interface (v115)

SHAMS remains the authority. External optimizers can only *propose* inputs.
SHAMS then re-evaluates proposals using frozen physics+constraints and emits an audit.

This module provides:
- template_request(): contract template for external optimizers
- template_response(): contract template for external optimizer proposals
- evaluate_optimizer_proposal(response_payload): evaluates proposed_inputs via SHAMS physics and returns a run_artifact + decision context
- build_optimizer_import_pack(...): zip with request/response templates, evaluated artifact, and justification

No physics changes. No solver changes.
"""

from typing import Any, Dict, Optional, List
import time
import json
import hashlib
from io import BytesIO
import zipfile

def _created_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def template_request(version: str = "v115") -> Dict[str, Any]:
    return {
        "kind": "shams_optimizer_request",
        "version": version,
        "created_utc": _created_utc(),
        "constraints_frozen": True,
        "feasible_region_ref": None,
        "objective_hint": "Provide candidate points; SHAMS will evaluate feasibility and annotate tradeoffs.",
        "candidate_space": {
            "levers": {
                "R0_m": [1.0, 4.0],
                "a_m": [0.3, 1.2],
                "Bt_T": [4.0, 18.0],
                "Ip_MA": [1.0, 20.0],
                "kappa": [1.2, 2.6],
                "fG": [0.2, 1.2],
                "Ti_keV": [5.0, 30.0],
                "Paux_MW": [0.0, 120.0],
            },
            "notes": [
                "Bounds are examples. External optimizer may use tighter ranges.",
                "Do not assume feasibility outside SHAMS validation.",
            ],
        },
        "notes": [
            "This is a contract template. External optimizer MUST NOT modify SHAMS physics/constraints.",
            "Optimizer output must be treated as a proposal; SHAMS re-evaluates everything.",
        ],
    }

def template_response(version: str = "v115") -> Dict[str, Any]:
    return {
        "kind": "shams_optimizer_response",
        "version": version,
        "created_utc": _created_utc(),
        "proposed_inputs": {
            "R0_m": 2.0, "a_m": 0.65, "kappa": 1.8,
            "Bt_T": 12.0, "Ip_MA": 8.0,
            "Ti_keV": 15.0, "fG": 0.8, "Paux_MW": 20.0,
        },
        "confidence": None,
        "assumptions": [
            "Proposal generated externally. SHAMS must validate feasibility.",
        ],
        "violations": [],
        "notes": [],
    }

def evaluate_optimizer_proposal(
    response_payload: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a SHAMS run artifact for proposed_inputs + an import context object."""
    if not (isinstance(response_payload, dict) and response_payload.get("kind") == "shams_optimizer_response"):
        raise ValueError("expected shams_optimizer_response dict")

    proposed = response_payload.get("proposed_inputs", {})
    if not isinstance(proposed, dict):
        raise ValueError("proposed_inputs must be a dict")

    # Evaluate using frozen physics path
    from models.inputs import PointInputs
    from physics.hot_ion import hot_ion_point
    from constraints.constraints import evaluate_constraints
    from shams_io.run_artifact import build_run_artifact

    # Filter to PointInputs accepted fields (best-effort: ignore unknown keys)
    # PointInputs(**dict) will raise if unknown; we defensively pick known via annotation if available.
    # Fallback: try constructing and let it raise with a clear error.
    pi = PointInputs(**proposed)  # type: ignore[arg-type]
    outputs = hot_ion_point(pi)
    constraints = evaluate_constraints(outputs)

    md = {"mode": "optimizer_import_v115", "source": "external_optimizer"}
    if isinstance(meta, dict):
        md.update(meta)

    art = build_run_artifact(inputs=pi.to_dict(), outputs=outputs, constraints=constraints, meta=md)

    context = {
        "kind": "shams_optimizer_import_context",
        "version": "v115",
        "created_utc": _created_utc(),
        "proposal_meta": {
            "confidence": response_payload.get("confidence"),
            "assumptions": response_payload.get("assumptions"),
            "violations": response_payload.get("violations"),
            "notes": response_payload.get("notes"),
        },
        "result": {
            "artifact_id": art.get("id"),
            "feasible": (art.get("constraints_summary") or {}).get("feasible") if isinstance(art.get("constraints_summary"), dict) else None,
            "worst_hard": (art.get("constraints_summary") or {}).get("worst_hard") if isinstance(art.get("constraints_summary"), dict) else None,
        },
        "disclaimer": "External optimizer proposals are not trusted. SHAMS re-evaluates physics+constraints.",
    }

    return {"artifact": art, "context": context}

def build_optimizer_import_pack(
    *,
    request_template: Dict[str, Any],
    response_template: Dict[str, Any],
    evaluated_artifact: Optional[Dict[str, Any]] = None,
    import_context: Optional[Dict[str, Any]] = None,
    version: str = "v115",
) -> Dict[str, Any]:
    created = _created_utc()
    req_bytes = json.dumps(request_template, indent=2, sort_keys=True).encode("utf-8")
    resp_bytes = json.dumps(response_template, indent=2, sort_keys=True).encode("utf-8")
    eva_bytes = json.dumps(evaluated_artifact, indent=2, sort_keys=True).encode("utf-8") if isinstance(evaluated_artifact, dict) else None
    ctx_bytes = json.dumps(import_context, indent=2, sort_keys=True).encode("utf-8") if isinstance(import_context, dict) else None

    manifest = {
        "kind": "shams_optimizer_import_pack_manifest",
        "version": version,
        "created_utc": created,
        "files": {
            "optimizer_request_template.json": {"sha256": _sha256_bytes(req_bytes), "bytes": len(req_bytes)},
            "optimizer_response_template.json": {"sha256": _sha256_bytes(resp_bytes), "bytes": len(resp_bytes)},
        },
        "notes": [
            "This pack defines the external optimizer contract and includes an evaluated example (if provided).",
        ],
    }
    if eva_bytes is not None:
        manifest["files"]["evaluated_run_artifact.json"] = {"sha256": _sha256_bytes(eva_bytes), "bytes": len(eva_bytes)}
    if ctx_bytes is not None:
        manifest["files"]["optimizer_import_context.json"] = {"sha256": _sha256_bytes(ctx_bytes), "bytes": len(ctx_bytes)}

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest["files"]["manifest.json"] = {"sha256": _sha256_bytes(manifest_bytes), "bytes": len(manifest_bytes)}

    zbuf = BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("optimizer_request_template.json", req_bytes)
        z.writestr("optimizer_response_template.json", resp_bytes)
        if eva_bytes is not None:
            z.writestr("evaluated_run_artifact.json", eva_bytes)
        if ctx_bytes is not None:
            z.writestr("optimizer_import_context.json", ctx_bytes)
        z.writestr("manifest.json", manifest_bytes)

    return {
        "kind": "shams_optimizer_import_pack",
        "version": version,
        "created_utc": created,
        "manifest": manifest,
        "zip_bytes": zbuf.getvalue(),
    }
