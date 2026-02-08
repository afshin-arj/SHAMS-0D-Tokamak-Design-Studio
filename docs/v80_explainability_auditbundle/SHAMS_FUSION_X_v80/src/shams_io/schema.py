from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import copy

# NOTE: SHAMS keeps artifacts deliberately simple and portable (pure JSON).
# This module defines a lightweight "schema contract" and validation routines.
# It is intentionally not a full JSON-Schema dependency.

CURRENT_SCHEMA_VERSION = "run_artifact.v2"

REQUIRED_TOP_LEVEL_KEYS_V2 = (
    "schema_version",
    "created_unix",
    "shams_version",
    "mode",
    "provenance",
    "inputs",
    "outputs",
    "constraints",
)

OPTIONAL_TOP_LEVEL_KEYS_V2 = (
    "label",
    "notes",
    "solver",
    "economics",
    "validation",
    "plots",
    "studies",
    "constraints_summary",
)

def validate_artifact(artifact: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable validation errors (empty if valid)."""
    errs: List[str] = []
    if not isinstance(artifact, dict):
        return ["artifact is not a dict"]

    sv = artifact.get("schema_version")
    if sv is None:
        errs.append("missing schema_version")
    elif not isinstance(sv, str):
        errs.append("schema_version must be a string")

    # v2 contract
    if sv == CURRENT_SCHEMA_VERSION:
        for k in REQUIRED_TOP_LEVEL_KEYS_V2:
            if k not in artifact:
                errs.append(f"missing required top-level key: {k}")
        if "inputs" in artifact and not isinstance(artifact["inputs"], dict):
            errs.append("inputs must be an object/dict")
        if "outputs" in artifact and not isinstance(artifact["outputs"], dict):
            errs.append("outputs must be an object/dict")
        if "constraints" in artifact and not isinstance(artifact["constraints"], list):
            errs.append("constraints must be a list")
        if "provenance" in artifact and not isinstance(artifact["provenance"], dict):
            errs.append("provenance must be an object/dict")
    else:
        # For older schemas we keep it permissive; migration handles normalization.
        # Still check for obviously broken forms.
        if "created_unix" not in artifact:
            errs.append("missing created_unix")
        if "outputs" in artifact and not isinstance(artifact["outputs"], dict):
            errs.append("outputs must be an object/dict")
    return errs


def normalize_v2(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Return a defensively-copied artifact normalized to the v2 contract."""
    a = copy.deepcopy(artifact)
    a.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    a.setdefault("mode", "point")
    a.setdefault("inputs", {})
    a.setdefault("outputs", {})
    a.setdefault("constraints", [])
    a.setdefault("provenance", {})
    a.setdefault("shams_version", a.get("shams_version", "unknown"))
    a.setdefault("created_unix", float(a.get("created_unix", 0.0)))
    # Normalize sections that are commonly absent
    a.setdefault("solver", {})
    a.setdefault("economics", {})
    a.setdefault("validation", {})
    a.setdefault("plots", {})
    a.setdefault("studies", {})
    # Ensure dict types
    if not isinstance(a["inputs"], dict): a["inputs"] = {}
    if not isinstance(a["outputs"], dict): a["outputs"] = {}
    if not isinstance(a["constraints"], list): a["constraints"] = []
    if not isinstance(a["provenance"], dict): a["provenance"] = {}
    return a
