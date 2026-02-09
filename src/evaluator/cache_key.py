from __future__ import annotations

"""
Deterministic cache key utilities for SHAMS evaluator memoization.

This must NEVER affect truth outputs; it only stabilizes memoization behavior
across Python processes and hash seeds.

Design goals:
- canonical, reviewer-safe serialization (sorted keys, stable float tokens)
- SHA-256 key (hex) for cache lookup
- no dependency on non-deterministic Python hashing

Author: © 2026 Afshin Arjhangmehr
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict
import hashlib
import json
import math


def _canon(x: Any) -> Any:
    """Canonicalize to JSON-safe primitives with stable float handling."""
    # Dataclasses -> dict
    if is_dataclass(x):
        return _canon(asdict(x))

    # Dict -> recurse with sorted keys (enforced later by json.dumps(sort_keys=True))
    if isinstance(x, dict):
        return {str(k): _canon(v) for k, v in x.items()}

    # List/Tuple -> list
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]

    # Floats -> stable tokens (strings) so JSON serialization is version-stable
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        # repr(float) is round-trip and stable for a given value
        return repr(float(x))

    # Int/bool/str/None are already JSON-safe
    if x is None or isinstance(x, (bool, int, str)):
        return x

    # Other numeric-like types
    try:
        # numpy scalars etc.
        if hasattr(x, "item"):
            return _canon(x.item())
    except Exception:
        pass

    # Fallback: stable string representation
    return str(x)


def canonical_json(obj: Any) -> str:
    """Return canonical JSON string for obj (sorted keys, no whitespace)."""
    canon = _canon(obj)
    return json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_cache_key(inp: Any) -> str:
    """Compute SHA-256 hex digest of canonical JSON of inputs."""
    # Prefer __dict__ for frozen dataclasses too; asdict is handled above.
    payload: Any
    if is_dataclass(inp):
        payload = inp
    else:
        payload = getattr(inp, "__dict__", inp)
    s = canonical_json(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
