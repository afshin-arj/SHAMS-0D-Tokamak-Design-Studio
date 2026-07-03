"""AST guard: all ui/*.py modules must not call hot_ion_point directly (Phase C)."""
from __future__ import annotations

import ast
from pathlib import Path


def _hot_ion_point_call_lines(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "hot_ion_point":
            lines.append(int(node.lineno))
    return sorted(lines)


def test_ui_modules_avoid_direct_hot_ion_point() -> None:
    ui_dir = Path(__file__).resolve().parents[1] / "ui"
    allowed = {
        ui_dir / "app.py",  # golden regen bypass only
    }
    violations: list[str] = []
    for path in sorted(ui_dir.rglob("*.py")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        calls = _hot_ion_point_call_lines(tree)
        if not calls:
            continue
        if path in allowed and len(calls) <= 1:
            continue
        violations.append(f"{path.relative_to(ui_dir.parent)}: lines {calls}")
    assert not violations, "Direct hot_ion_point in UI:\n" + "\n".join(violations)
