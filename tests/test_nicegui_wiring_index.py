from __future__ import annotations

from ui_nicegui.decks import DECK_LABELS, DECK_RENDERERS


def test_nicegui_deck_registry_complete() -> None:
    assert len(DECK_LABELS) == 10
    for deck in DECK_LABELS:
        assert deck in DECK_RENDERERS, f"Missing renderer for deck: {deck}"
        assert callable(DECK_RENDERERS[deck])


def test_nicegui_wiring_index_contains_anchors() -> None:
    from pathlib import Path
    from tools.nicegui_wiring_index import build_nicegui_wiring_index_markdown

    repo_root = Path(__file__).resolve().parents[1]
    md = build_nicegui_wiring_index_markdown(repo_root=repo_root)
    for s in [
        "NiceGUI UI Wiring Index",
        "Point Designer",
        "System Suite",
        "ui_evaluate",
        "DECK_RENDERERS",
        "Streamlit parallel",
    ]:
        assert s in md
