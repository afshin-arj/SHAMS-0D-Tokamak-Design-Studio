from __future__ import annotations

from typing import Any, Dict
from pathlib import Path
import json, zipfile, hashlib


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def export_phase_envelope_zip(envelope: Dict[str, Any], out_zip: Path) -> Path:
    """Export a deterministic, audit-safe Phase Envelopes ZIP.

    Members
    -------
    - phase_envelope.json (the envelope object)
    - phases/<name>.json (one run artifact per phase)
    - manifest.json (member hashes)
    """
    if not isinstance(envelope, dict) or not envelope:
        raise ValueError("envelope must be a non-empty dict")

    phases = envelope.get("phases_ordered") or []
    if not isinstance(phases, list):
        phases = []

    members: Dict[str, bytes] = {}
    env_bytes = json.dumps(envelope, sort_keys=True, indent=2).encode("utf-8")
    members["phase_envelope.json"] = env_bytes

    for i, art in enumerate(phases):
        name = ""
        try:
            name = str((art.get("phase") or {}).get("name", "")).strip()
        except Exception:
            name = ""
        safe = name if name else f"phase_{i:02d}"
        safe = "".join(ch if (ch.isalnum() or ch in ("-","_",".")) else "_" for ch in safe)
        key = f"phases/{safe}.json"
        members[key] = json.dumps(art, sort_keys=True, indent=2).encode("utf-8")

    manifest = {
        "schema_version": "phase_envelope_zip_manifest.v1",
        "members": {k: {"sha256": _sha256_bytes(v), "bytes": len(v)} for k, v in members.items()},
    }
    members["manifest.json"] = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for k, v in members.items():
            zf.writestr(zipfile.ZipInfo(k, date_time=(1980,1,1,0,0,0)), v)
    return out_zip
