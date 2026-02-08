"""SHAMS repository hygiene cleaner.

Hard rules (per project law):
 - No __pycache__/ or .pytest_cache/ in a release tree
 - No stray UI folders (e.g., gspulse_ui/)
 - No run_st* launchers
 - No compiled artifacts (*.pyc, *.pyo)

This script is intentionally *side-effect only* on the working tree and does not
touch any physics/evaluator content beyond deleting forbidden cache artifacts.

Author: © 2026 Afshin Arjhangmehr
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FORBIDDEN_DIR_NAMES = (
    "__pycache__",
    ".pytest_cache",
    "gspulse_ui",
)

FORBIDDEN_GLOBS = (
    "run_st*",
    "*.pyc",
    "*.pyo",
)


@dataclass(frozen=True)
class HygieneReport:
    removed_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]


def _rm_tree(p: Path) -> bool:
    if not p.exists():
        return False
    if p.is_dir():
        # Robust recursive delete without relying on shutil.rmtree edge cases.
        for child in p.rglob("*"):
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
            except Exception:
                # Best-effort; continue.
                pass
        # Remove directories bottom-up
        for d in sorted([x for x in p.rglob("*") if x.is_dir()], key=lambda x: len(str(x)), reverse=True):
            try:
                d.rmdir()
            except Exception:
                pass
        try:
            p.rmdir()
        except Exception:
            pass
        return not p.exists()
    try:
        p.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def clean_repo(root: Path) -> HygieneReport:
    """Remove forbidden artifacts from the repository tree.

    Notes
    -----
    - Does *not* delete .venv (user environment) even if it contains caches.
    - Only deletes forbidden names/globs outside of .venv.
    """

    root = root.resolve()
    removed: list[str] = []
    missing: list[str] = []

    def _is_under_venv(p: Path) -> bool:
        try:
            return ".venv" in p.relative_to(root).parts
        except Exception:
            return False

    # Remove forbidden directories by name.
    for name in FORBIDDEN_DIR_NAMES:
        for d in root.rglob(name):
            if _is_under_venv(d):
                continue
            if _rm_tree(d):
                removed.append(str(d))
            else:
                missing.append(str(d))

    # Remove forbidden globs.
    for pat in FORBIDDEN_GLOBS:
        for p in root.rglob(pat):
            if _is_under_venv(p):
                continue
            if _rm_tree(p):
                removed.append(str(p))
            else:
                missing.append(str(p))

    return HygieneReport(tuple(sorted(set(removed))), tuple(sorted(set(missing))))


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Clean SHAMS repo hygiene artifacts.")
    ap.add_argument("--root", default=".", help="Repo root (default: current directory)")
    ap.add_argument("--report", default="hygiene_clean_report.json", help="Write report JSON (default: hygiene_clean_report.json)")
    args = ap.parse_args(argv)

    rep = clean_repo(Path(args.root))
    out = {
        "removed_paths": list(rep.removed_paths),
        "missing_paths": list(rep.missing_paths),
    }
    try:
        Path(args.report).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass

    print(f"Removed {len(rep.removed_paths)} paths")
    if rep.missing_paths:
        print(f"Warnings: failed to remove {len(rep.missing_paths)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
