"""Test bootstrap for SHAMS.

Pytest is run with --import-mode=importlib to avoid path leakage.
For SHAMS, we intentionally support importing modules both as:
  - models.* (when repo_root/src is on sys.path)
  - src.* (when repo_root is on sys.path)

This conftest makes the test environment mirror the UI/CLI environment.
"""

from __future__ import annotations

import os
import sys


# Repo hygiene law: never write bytecode caches into the working tree.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(REPO_ROOT, "src")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)
