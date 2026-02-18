from __future__ import annotations

"""Compatibility shim.

Historically the app imported `render_extopt_suite` from `ui.extopt_suite`.
The canonical implementation lives in `ui.optimizer_suite`.

This file preserves the stable import path to avoid UI regression.
"""

from pathlib import Path

from .optimizer_suite import render_external_optimizer_suite


def render_extopt_suite(repo_root: Path) -> None:
    return render_external_optimizer_suite(repo_root)
