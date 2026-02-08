from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_dumps(obj: Any) -> str:
    """Deterministic JSON serialization (for hashing/caching)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_sha256(obj: Any) -> str:
    """Stable SHA256 of a JSON-serializable object."""
    b = stable_json_dumps(obj).encode("utf-8")
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()
