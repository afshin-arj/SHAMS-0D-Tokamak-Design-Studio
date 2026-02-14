from __future__ import annotations

from typing import Any, Dict
from pathlib import Path
import json, zipfile, hashlib


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def export_uncertainty_contract_zip(contract: Dict[str, Any], out_zip: Path) -> Path:
    """Export a deterministic, audit-safe Uncertainty Contracts ZIP.

    Members
    -------
    - uncertainty_contract.json (the contract object)
    - corners/corner_XXXX.json (one run artifact per corner)
    - manifest.json (member hashes)
    """
    if not isinstance(contract, dict) or not contract:
        raise ValueError("contract must be a non-empty dict")

    corners = contract.get("corners") or []
    if not isinstance(corners, list):
        corners = []

    members: Dict[str, bytes] = {}
    con_bytes = json.dumps(contract, sort_keys=True, indent=2).encode("utf-8")
    members["uncertainty_contract.json"] = con_bytes

    for i, art in enumerate(corners):
        key = f"corners/corner_{i:04d}.json"
        members[key] = json.dumps(art, sort_keys=True, indent=2).encode("utf-8")

    manifest = {
        "schema_version": "uncertainty_contract_zip_manifest.v1",
        "members": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k, v in members.items()},
    }
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for k, v in members.items():
            zf.writestr(zipfile.ZipInfo(k, date_time=(1980,1,1,0,0,0)), v)
    return out_zip
