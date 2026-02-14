from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict


def _repo_root(start: Path) -> Path:
    """Best-effort repo root discovery.

    We keep this heuristic and dependency-light for Windows compatibility.
    """
    cur = start.resolve()
    for _ in range(12):
        if (cur / "requirements.txt").exists() or (cur / ".git").exists() or (cur / "pyproject.toml").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def _read_text_if_exists(p: Path, *, max_chars: int = 4000) -> str:
    try:
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")[:max_chars].strip()
    except Exception:
        pass
    return ""


def collect_provenance(start: Path | None = None) -> Dict[str, Any]:
    """Collect minimal provenance for auditability.

    This is intentionally conservative:
    - no network calls
    - no git commands required
    - safe on Windows
    """
    if start is None:
        start = Path(__file__).resolve()
    root = _repo_root(Path(start))

    prov: Dict[str, Any] = {
        "created_unix": float(time.time()),
        "python": sys.version.split("\n")[0],
        "platform": platform.platform(),
        "pid": int(os.getpid()),
    }

    # Optional repo version marker
    ver = _read_text_if_exists(root / "VERSION", max_chars=200)
    if ver:
        prov["repo_version"] = ver.splitlines()[0].strip()

    # Optional git commit marker written by CI or release pipeline
    git_commit = _read_text_if_exists(root / "GIT_COMMIT", max_chars=200)
    if git_commit:
        prov["git_commit"] = git_commit.splitlines()[0].strip()
    else:
        env_commit = os.environ.get("GIT_COMMIT") or os.environ.get("GITHUB_SHA")
        if env_commit:
            prov["git_commit"] = str(env_commit)[:40]

    return prov
