"""AST guard: ui_nicegui/**/*.py must not call hot_ion_point or bare Evaluator()."""
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


def _evaluator_ctor_lines(tree: ast.AST) -> list[int]:
    """Detect Evaluator(...) constructions (Name or Attribute)."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "Evaluator":
            lines.append(int(node.lineno))
        elif isinstance(func, ast.Attribute) and func.attr == "Evaluator":
            lines.append(int(node.lineno))
    return sorted(lines)


def test_nicegui_modules_avoid_direct_hot_ion_point() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ui_dir = repo_root / "ui_nicegui"
    allowed: set[Path] = set()

    violations: list[str] = []
    for path in sorted(ui_dir.rglob("*.py")):
        if path.name.startswith("_") and path.name != "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        calls = _hot_ion_point_call_lines(tree)
        if not calls:
            continue
        if path in allowed and len(calls) <= 1:
            continue
        violations.append(f"{path.relative_to(repo_root).as_posix()}: lines {calls}")
    assert not violations, "Direct hot_ion_point in NiceGUI UI:\n" + "\n".join(violations)


def test_nicegui_modules_avoid_bare_evaluator_ctor() -> None:
    """Only ui_nicegui/evaluate.py may construct Evaluator(); others use ui_evaluator()."""
    repo_root = Path(__file__).resolve().parents[1]
    ui_dir = repo_root / "ui_nicegui"
    allowed = {ui_dir / "evaluate.py"}

    violations: list[str] = []
    for path in sorted(ui_dir.rglob("*.py")):
        if path.name.startswith("_") and path.name != "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        calls = _evaluator_ctor_lines(tree)
        if not calls:
            continue
        if path.resolve() in {p.resolve() for p in allowed}:
            continue
        violations.append(f"{path.relative_to(repo_root).as_posix()}: lines {calls}")
    assert not violations, "Bare Evaluator() outside evaluate.py:\n" + "\n".join(violations)


def test_ui_evaluate_forwards_origin_as_label() -> None:
    import inspect

    from ui_nicegui import evaluate as ev

    src = inspect.getsource(ev.ui_evaluate)
    assert 'setdefault("label"' in src or "setdefault('label'" in src
    assert "ui_evaluator" in inspect.getsource(ev)
    adapter = ev.ui_evaluator(origin="NiceGUI:TestOrigin")
    assert adapter.label == "NiceGUI:TestOrigin"
    assert adapter.origin == "NiceGUI:TestOrigin"
