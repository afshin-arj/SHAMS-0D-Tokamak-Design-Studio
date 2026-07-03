"""Compatibility layer for absolute imports.

Authoritative implementations live under `src/constraints`.
This module re-exports the stable public surface.

© 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from src.constraints import *  # noqa: F401,F403
from src.constraints import __all__ as __all__  # type: ignore
