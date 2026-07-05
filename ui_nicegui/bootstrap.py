"""Import path bootstrap for NiceGUI entrypoints.

Ensures repo root and src/ are on sys.path so legacy `evaluator.*` imports
inside src/ modules resolve when running `python ui_nicegui/app.py` directly.
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_ROOT = os.path.join(_REPO_ROOT, "src")


def ensure_import_paths() -> str:
    """Insert repo root and src/ at the front of sys.path; return repo root."""
    for path in (_REPO_ROOT, _SRC_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)
    return _REPO_ROOT


def repo_root() -> str:
    return _REPO_ROOT
