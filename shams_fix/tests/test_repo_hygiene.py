from __future__ import annotations

from pathlib import Path


FORBIDDEN_DIR_NAMES = ("__pycache__", ".pytest_cache", "gspulse_ui")
FORBIDDEN_GLOBS = ("run_st*", "*.pyc", "*.pyo")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_under_venv(p: Path, root: Path) -> bool:
    try:
        return ".venv" in p.relative_to(root).parts
    except Exception:
        return False


def _is_under_tests_cache(p: Path, root: Path) -> bool:
    """Pytest may transiently compile `conftest.py`.

    We still clean these artifacts before packaging (launcher + hygiene_clean.py),
    but do not fail the test suite on this transient behavior.
    """
    try:
        parts = p.relative_to(root).parts
        return len(parts) >= 2 and parts[0] == "tests" and parts[1] == "__pycache__"
    except Exception:
        return False


def test_release_tree_has_no_forbidden_artifacts() -> None:
    """Release hygiene gate.

    This enforces the permanent rule that packaged SHAMS trees do not contain
    cache dirs, compiled artifacts, or stray launchers.
    """

    root = _repo_root()
    hits: list[str] = []

    for name in FORBIDDEN_DIR_NAMES:
        for p in root.rglob(name):
            if _is_under_venv(p, root):
                continue
            if _is_under_tests_cache(p, root):
                continue
            hits.append(str(p))

    for pat in FORBIDDEN_GLOBS:
        for p in root.rglob(pat):
            if _is_under_venv(p, root):
                continue
            if _is_under_tests_cache(p, root):
                continue
            hits.append(str(p))

    assert not hits, "Hygiene violations detected:\n" + "\n".join(sorted(set(hits)))
