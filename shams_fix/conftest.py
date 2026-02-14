"""Repository-wide pytest bootstrap for SHAMS.

This file exists to ensure imports work in all environments, including those where
collection starts before tests/conftest.py is applied.

SHAMS supports importing modules both as:
  - models.* (when repo_root/src is on sys.path)
  - src.* (when repo_root is on sys.path)

Repo hygiene law: do not write bytecode caches.
"""

from __future__ import annotations

import os
import sys

# Hygiene: never write bytecode caches into the working tree.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC = os.path.join(REPO_ROOT, "src")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)
