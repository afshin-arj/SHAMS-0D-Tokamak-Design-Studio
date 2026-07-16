"""Export bundle with SHA-256 manifest (UI Phase D)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def build_export_bundle(
    *,
    deck: str,
    outputs: Dict[str, Any],
    inputs: Optional[Dict[str, Any]] = None,
    constraints: Optional[Any] = None,
    extra: Optional[Dict[str, Any]] = None,
    design_intent: Optional[str] = None,
    no_solution_atlas: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "deck": deck,
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": inputs or {},
        "outputs": outputs,
    }
    if constraints is not None:
        payload["constraints"] = constraints
    if extra:
        payload["extra"] = extra

    # Independence ticket 1.1: infeasible point exports include no_solution_atlas.v1.
    atlas = no_solution_atlas if isinstance(no_solution_atlas, dict) else None
    if atlas is None:
        try:
            try:
                from diagnostics.no_solution_atlas import build_no_solution_atlas  # type: ignore
            except ImportError:
                from src.diagnostics.no_solution_atlas import build_no_solution_atlas  # type: ignore
            intent = design_intent
            if intent is None and isinstance(inputs, dict):
                intent = inputs.get("design_intent") or inputs.get("intent")
            built = build_no_solution_atlas(
                outputs if isinstance(outputs, dict) else {},
                design_intent=str(intent) if intent else None,
            )
            if str(built.get("verdict", "")) == "INFEASIBLE":
                atlas = built
        except Exception:
            # Fail-closed stub: do not invent FEASIBLE; omit only if we cannot
            # tell infeasibility from outputs (caller may still pass prebuilt).
            atlas = {
                "schema": "no_solution_atlas.v1",
                "verdict": "UNKNOWN",
                "dominant_constraint": "",
                "dominant_mechanism": "GENERAL",
                "mechanism_map": {},
                "hard_failures": [],
                "n_hard_failures": 0,
                "parity_aligned": True,
                "atlas_build_error": True,
            }
    if isinstance(atlas, dict) and atlas.get("schema") == "no_solution_atlas.v1":
        # Stamp when infeasible, UNKNOWN fail-closed stub, or caller passed prebuilt.
        if (
            no_solution_atlas is not None
            or str(atlas.get("verdict", "")) in {"INFEASIBLE", "UNKNOWN"}
            or bool(atlas.get("atlas_build_error"))
        ):
            if str(atlas.get("verdict", "")) != "FEASIBLE" or no_solution_atlas is not None:
                payload["no_solution_atlas"] = atlas

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["manifest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def bundle_json_bytes(bundle: Dict[str, Any]) -> bytes:
    return json.dumps(bundle, indent=2, sort_keys=True, default=str).encode("utf-8")
