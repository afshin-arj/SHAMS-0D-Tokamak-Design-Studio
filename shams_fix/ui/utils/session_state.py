"""Streamlit session_state helpers.

Author: (c) 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from typing import Any, Optional


def ss_get_bool(ss: Any, key: str, default: bool) -> bool:
    """Get a bool from session_state; return default if missing/invalid."""
    try:
        v = ss[key]
    except Exception:
        v = default
    try:
        return bool(v)
    except Exception:
        return bool(default)


def ss_get_int(
    ss: Any,
    key: str,
    default: int,
    *,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Get an int from session_state; clamp to [min_value, max_value] if set."""
    try:
        v = ss[key]
    except Exception:
        v = default
    try:
        x = int(v)
    except Exception:
        x = int(default)
    if min_value is not None and x < min_value:
        x = min_value
    if max_value is not None and x > max_value:
        x = max_value
    return x


def ss_setdefault(ss: Any, key: str, value: Any) -> Any:
    """Set ss[key] = value if key missing; return ss[key]."""
    try:
        if key not in ss:
            ss[key] = value
        return ss[key]
    except Exception:
        return value
