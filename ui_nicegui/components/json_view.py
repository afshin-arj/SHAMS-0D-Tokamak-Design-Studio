"""JSON blob display for NiceGUI 3.x (ui.json removed)."""
from __future__ import annotations

import json
from typing import Any

from nicegui import ui


def render_json_blob(data: Any, *, max_chars: int = 8000) -> None:
    try:
        text = json.dumps(data, indent=2, default=str, sort_keys=True)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n… [truncated]"
    ui.code(text, language="json").classes("w-full")
