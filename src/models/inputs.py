"""Backward-compatibility shim.

``PointInputs`` was moved to :mod:`schema.inputs` in Tier-3 Batch B1 (schema
extraction). This module re-exports it so existing imports such as
``from models.inputs import PointInputs`` (and ``from src.models.inputs import
PointInputs``) keep working unchanged. New code should import from
``schema.inputs`` directly.
"""
from __future__ import annotations

try:
    # When ``src/`` is on sys.path (application/runtime, conftest test bootstrap).
    from schema.inputs import PointInputs  # type: ignore  # noqa: F401
except ImportError:
    # When the repository root is on sys.path (``import src.*``).
    from src.schema.inputs import PointInputs  # type: ignore  # noqa: F401

__all__ = ["PointInputs"]
