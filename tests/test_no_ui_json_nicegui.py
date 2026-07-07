"""Guard: NiceGUI 3.x removed ui.json — decks must use render_json_blob."""
from __future__ import annotations

from pathlib import Path


def test_no_ui_json_calls_in_ui_nicegui() -> None:
    root = Path(__file__).resolve().parents[1] / "ui_nicegui"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ui.json(" in text:
            offenders.append(str(path.relative_to(root.parent)))
    assert not offenders, f"ui.json still used: {offenders}"
