"""Build deterministic repo SHA256 manifests.

Writes:
  - MANIFEST_SHA256.txt: sha256 <space><space> relative path for tracked files
  - MANIFEST_UPGRADE_SHA256.txt: same format for a caller-provided list

This script is reviewer-safe and performs no truth/physics execution.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from typing import Iterable, List, Sequence


FORBIDDEN_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_forbidden(p: Path) -> bool:
    parts = set(p.parts)
    return any(d in parts for d in FORBIDDEN_DIRS) or p.name.endswith(".pyc")


def iter_repo_files(repo_root: Path) -> List[Path]:
    files: List[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if _is_forbidden(rel):
            continue
        # Avoid self-recursion: do not include manifests themselves in MANIFEST_SHA256
        if rel.as_posix() in {"MANIFEST_SHA256.txt", "MANIFEST_UPGRADE_SHA256.txt"}:
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(repo_root).as_posix())
    return files


def write_manifest(repo_root: Path, out_path: Path, files: Sequence[Path]) -> None:
    lines = []
    for p in files:
        rel = p.relative_to(repo_root).as_posix()
        lines.append(f"{_sha256_file(p)}  {rel}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_upgrade_manifest(repo_root: Path, out_path: Path, rel_paths: Iterable[str]) -> None:
    files: List[Path] = []
    for rp in rel_paths:
        p = (repo_root / rp).resolve()
        if not p.exists() or not p.is_file():
            # silently skip missing: upgrade manifests are advisory
            continue
        files.append(p)
    files.sort(key=lambda x: x.relative_to(repo_root).as_posix())
    write_manifest(repo_root, out_path, files)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=str, default=".", help="Repo root")
    ap.add_argument("--write_upgrade", action="store_true", help="Also rewrite MANIFEST_UPGRADE_SHA256.txt")
    ap.add_argument(
        "--upgrade_paths",
        type=str,
        default="",
        help="Comma-separated list of relative paths to include in MANIFEST_UPGRADE_SHA256.txt",
    )
    args = ap.parse_args()
    repo_root = Path(args.repo).resolve()

    files = iter_repo_files(repo_root)
    write_manifest(repo_root, repo_root / "MANIFEST_SHA256.txt", files)

    if args.write_upgrade:
        rels = [x.strip() for x in (args.upgrade_paths or "").split(",") if x.strip()]
        write_upgrade_manifest(repo_root, repo_root / "MANIFEST_UPGRADE_SHA256.txt", rels)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
