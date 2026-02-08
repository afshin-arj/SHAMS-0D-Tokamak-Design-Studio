"""Compatibility layer for absolute imports.

Authoritative implementations live under `src/constraints`.
This module re-exports the stable public surface.

© 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

try:
    from src.constraints.system import build_constraints_from_outputs  # type: ignore
    from src.constraints.system import summarize_constraints  # type: ignore
except Exception:  # pragma: no cover
    # Fallback for runtime contexts that already have `src` on the path.
    from constraints.system import build_constraints_from_outputs  # type: ignore
    from constraints.system import summarize_constraints  # type: ignore

__all__ = [
    "build_constraints_from_outputs",
    "summarize_constraints",
]
