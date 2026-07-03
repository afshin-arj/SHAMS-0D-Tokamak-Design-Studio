"""PROPOSAL-008: UI must route point evaluation through Evaluator choke point."""
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


def test_ui_app_uses_evaluator_choke_point() -> None:
    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    text = app_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(app_path))
    calls = _hot_ion_point_call_lines(tree)
    assert len(calls) <= 1, (
        "ui/app.py should have at most one direct hot_ion_point call (golden regen bypass). "
        f"Found calls at lines: {calls}"
    )
    if calls:
        lineno = calls[0]
        window = "\n".join(text.splitlines()[max(0, lineno - 4) : lineno])
        assert "Golden parity" in window, (
            f"Direct hot_ion_point at line {lineno} must be documented as golden-parity bypass"
        )


def test_ui_evaluate_helper_exists() -> None:
    app_path = Path(__file__).resolve().parents[1] / "ui" / "app.py"
    text = app_path.read_text(encoding="utf-8")
    assert "def _ui_evaluate(" in text
    assert "PROPOSAL-008" in text
