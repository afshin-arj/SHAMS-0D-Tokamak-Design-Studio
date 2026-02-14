from __future__ import annotations

from typing import Any, Dict
from .schema import CURRENT_SCHEMA_VERSION, normalize_v2

def migrate_artifact(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate any older artifact dict to the current schema version.

    Strategy: be conservative, preserve unknown keys, but ensure required
    sections exist so downstream tools don't crash.
    """
    sv = artifact.get("schema_version")
    if sv == CURRENT_SCHEMA_VERSION:
        return normalize_v2(artifact)

    # v1 -> v2 heuristics
    a = dict(artifact)  # shallow copy ok; normalize will deep copy
    a["schema_version"] = CURRENT_SCHEMA_VERSION

    # Common older keys
    if "outputs" not in a and "out" in a:
        a["outputs"] = a.get("out", {}) or {}
    if "inputs" not in a and "inp" in a:
        a["inputs"] = a.get("inp", {}) or {}
    if "constraints" not in a and "constraint_list" in a:
        a["constraints"] = a.get("constraint_list", []) or []

    return normalize_v2(a)
