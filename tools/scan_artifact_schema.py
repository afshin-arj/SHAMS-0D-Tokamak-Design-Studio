from __future__ import annotations

"""Scan Lab artifact schema (v1) and upgrader.

Why:
 - Scan Lab must be freeze-grade: reproducible, replayable, and future-proof.
 - Schema v1 is locked; any future changes require an upgrader.

This module is intentionally light-weight (stdlib only).
"""

import hashlib
import json
from typing import Any, Dict, Optional


SCAN_SCHEMA_VERSION = 1


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(obj: Any) -> str:
    """Short, stable content hash for audit and determinism checks."""
    b = _stable_json(obj).encode("utf-8")
    return hashlib.sha256(b).hexdigest()[:16]


REASON_CODES_V1 = {
    "ok",
    "import_error",
    "bad_bounds",
    "run_ok",
    "export_ok",
    "export_error",
}


def upgrade_scan_artifact(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade a scan artifact to schema v1.

    This is *idempotent*. If obj is already schema v1, it is returned unchanged.
    """
    if not isinstance(obj, dict):
        return {"scan_schema_version": SCAN_SCHEMA_VERSION, "payload": obj}

    v = int(obj.get("scan_schema_version", 0) or 0)
    if v == SCAN_SCHEMA_VERSION:
        return obj

    # v0 -> v1 normalization
    out = dict(obj)
    out["scan_schema_version"] = SCAN_SCHEMA_VERSION

    # Ensure canonical fields exist
    out.setdefault("reason_code", "run_ok")
    if out["reason_code"] not in REASON_CODES_V1:
        out["reason_code"] = "run_ok"

    out.setdefault("freeze_statement", "Scan Lab is frozen: schema v1")
    out.setdefault("report_hash", stable_hash(out.get("report", {})))

    return out


def build_scan_artifact(
    *,
    report: Dict[str, Any],
    settings: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    reason_code: str = "run_ok",
    freeze_statement: str = "Scan Lab is frozen: schema v1",
) -> Dict[str, Any]:
    """Wrap a cartography report into a freeze-grade artifact."""
    art: Dict[str, Any] = {
        "scan_schema_version": SCAN_SCHEMA_VERSION,
        "reason_code": reason_code if reason_code in REASON_CODES_V1 else "run_ok",
        "freeze_statement": freeze_statement,
        "settings": settings or {},
        "report": report or {},
        "metadata": metadata or {},
    }
    art["report_hash"] = stable_hash(art.get("report", {}))
    art["artifact_hash"] = stable_hash({k: art[k] for k in ("scan_schema_version", "reason_code", "settings", "report_hash")})
    return art
