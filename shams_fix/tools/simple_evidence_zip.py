from __future__ import annotations

import io
import json
import time
import zipfile
from typing import Any, Dict, Optional


def build_simple_evidence_zip_bytes(
    payload: Dict[str, Any],
    *,
    basename: str,
    extra_files: Optional[Dict[str, bytes]] = None,
) -> bytes:
    """Build a deterministic evidence zip.

    The zip always contains:
      - evidence.json (sorted keys, indented)

    Optional extra files may be included via extra_files.
    File ordering is deterministic.
    """
    obj = dict(payload)
    obj.setdefault("schema_version", "evidence.simple.v1")
    obj.setdefault("basename", basename)
    obj.setdefault("created_unix", int(time.time()))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "evidence.json",
            json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False),
        )
        if isinstance(extra_files, dict) and extra_files:
            for name in sorted(extra_files.keys()):
                b = extra_files[name]
                if isinstance(b, (bytes, bytearray)) and len(b) > 0:
                    z.writestr(name, bytes(b))
    return buf.getvalue()
