from __future__ import annotations

"""UI helpers for Profile Contracts 2.0 (v362.0).

Provides deterministic export of a Profile Contracts report to a ZIP bundle.

© 2026 Afshin Arjhangmehr
"""

from typing import Any, Dict
from pathlib import Path
import json
import zipfile
import hashlib


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def export_profile_contracts_zip(report: Dict[str, Any], out_zip: Path) -> Path:
    """Export a deterministic, audit-safe Profile Contracts ZIP.

    Members
    -------
    - profile_contracts_report.json
    - corners/corner_XXXX.json
    - manifest.json
    """
    if not isinstance(report, dict) or not report:
        raise ValueError("report must be a non-empty dict")

    corners = report.get("corners") or []
    if not isinstance(corners, list):
        corners = []

    members: Dict[str, bytes] = {}
    rep_bytes = json.dumps(report, sort_keys=True, indent=2).encode("utf-8")
    members["profile_contracts_report.json"] = rep_bytes

    for i, corner in enumerate(corners):
        key = f"corners/corner_{i:04d}.json"
        members[key] = json.dumps(corner, sort_keys=True, indent=2).encode("utf-8")

    manifest = {
        "schema_version": "profile_contracts_zip_manifest.v1",
        "members": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k, v in members.items()},
    }
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for k, v in members.items():
            zf.writestr(zipfile.ZipInfo(k, date_time=(1980, 1, 1, 0, 0, 0)), v)
    return out_zip
