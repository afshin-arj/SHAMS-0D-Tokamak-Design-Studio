"""Guard against import-time NiceGUI calls in ui_nicegui helper modules.

`ui_nicegui/app.py` is the entrypoint and may build the shell at import/startup.
All other `ui_nicegui/**/*.py` modules must not call `ui.*` at module scope.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _has_nicegui_call(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            func = n.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "ui":
                return True
    return False


def test_no_import_time_nicegui_calls_in_helper_modules() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ui_dir = repo_root / "ui_nicegui"
    assert ui_dir.is_dir(), "ui_nicegui/ directory not found"

    exempt = {ui_dir / "app.py"}

    offenders: list[str] = []
    for path in sorted(ui_dir.rglob("*.py")):
        if path in exempt:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for stmt in tree.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and not _has_nicegui_call(stmt):
                continue
            if _has_nicegui_call(stmt):
                offenders.append(f"{path.relative_to(repo_root).as_posix()}: {type(stmt).__name__}")

    assert not offenders, (
        "Import-time NiceGUI calls detected in ui_nicegui helper modules:\n" + "\n".join(offenders)
    )
