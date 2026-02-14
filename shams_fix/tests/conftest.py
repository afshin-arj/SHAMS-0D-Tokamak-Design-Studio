"""Pytest session hygiene.

Prevents bytecode emission and cleans caches created during tests.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import sys


from pathlib import Path


def _purge(repo_root: Path) -> None:
    # Remove __pycache__ directories
    for d in repo_root.rglob("__pycache__"):
        try:
            for f in d.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            d.rmdir()
        except Exception:
            pass

    # Remove pytest cache
    for d in repo_root.rglob(".pytest_cache"):
        try:
            for f in d.rglob("*"):
                try:
                    if f.is_file():
                        f.unlink()
                except Exception:
                    pass
            for sub in sorted([p for p in d.rglob("*") if p.is_dir()], reverse=True):
                try:
                    sub.rmdir()
                except Exception:
                    pass
            d.rmdir()
        except Exception:
            pass

    # Remove stray .pyc
    for f in repo_root.rglob("*.pyc"):
        try:
            f.unlink()
        except Exception:
            pass


def pytest_sessionstart(session):
    sys.dont_write_bytecode = True
    repo_root = Path(__file__).resolve().parents[1]
    # Ensure repo-root and src/ are importable during tests
    rr = str(repo_root)
    rs = str(repo_root / "src")
    if rr not in sys.path:
        sys.path.insert(0, rr)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    _purge(repo_root)


def pytest_sessionfinish(session, exitstatus):
    repo_root = Path(__file__).resolve().parents[1]
    # Ensure repo-root and src/ are importable during tests
    rr = str(repo_root)
    rs = str(repo_root / "src")
    if rr not in sys.path:
        sys.path.insert(0, rr)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    _purge(repo_root)
