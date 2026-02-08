"""Guard against import-time Streamlit calls in UI helper modules.

`ui/app.py` is the Streamlit entrypoint and may contain top-level Streamlit calls.
All other `ui/*.py` modules must not call `st.*` at module scope.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _has_streamlit_call(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            func = n.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "st":
                return True
    return False


def test_no_import_time_streamlit_calls_in_ui_helper_modules():
    repo_root = Path(__file__).resolve().parents[1]
    ui_dir = repo_root / "ui"
    assert ui_dir.is_dir(), "ui/ directory not found"

    exempt = {"app.py", "__init__.py"}

    offenders = []
    for path in sorted(ui_dir.glob("*.py")):
        if path.name in exempt:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for stmt in tree.body:
            # Definitions and imports are allowed at module scope.
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            # Allow simple constant assignments without calls.
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and not _has_streamlit_call(stmt):
                continue
            if _has_streamlit_call(stmt):
                offenders.append(f"{path.as_posix()}: {type(stmt).__name__}")

    assert not offenders, "Import-time Streamlit calls detected in UI helper modules:\n" + "\n".join(offenders)
