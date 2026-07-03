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
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["manifest_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def bundle_json_bytes(bundle: Dict[str, Any]) -> bytes:
    return json.dumps(bundle, indent=2, sort_keys=True, default=str).encode("utf-8")
