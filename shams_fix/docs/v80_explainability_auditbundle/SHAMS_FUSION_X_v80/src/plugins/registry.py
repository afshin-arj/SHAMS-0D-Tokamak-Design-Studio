from __future__ import annotations
"""Lightweight plugin registry (PROCESS-inspired extensibility).

SHAMS stays dependency-free. This module provides a minimal mechanism to
register alternative model implementations (confinement, divertor, economics,
etc.) without hard-coding them into the core.

Plugins are *opt-in*: if none are registered, SHAMS behaves identically.
"""

from typing import Callable, Dict, Any

_REGISTRY: Dict[str, Dict[str, Callable[..., Any]]] = {}

def shams_plugin(kind: str, name: str):
    """Decorator to register a plugin function under a kind+name."""
    def _decorator(fn: Callable[..., Any]):
        _REGISTRY.setdefault(kind, {})[name] = fn
        return fn
    return _decorator

def get_plugin(kind: str, name: str) -> Callable[..., Any] | None:
    return _REGISTRY.get(kind, {}).get(name)

def list_plugins(kind: str) -> Dict[str, Callable[..., Any]]:
    return dict(_REGISTRY.get(kind, {}))
