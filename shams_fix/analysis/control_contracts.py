"""Compatibility wrapper for control contracts.

The primary implementation lives in :mod:`src.analysis.control_contracts`.
This wrapper exists to preserve the legacy import style `analysis.*`.
"""

from __future__ import annotations

from src.analysis.control_contracts import ControlContracts, compute_control_contracts  # noqa: F401
