"""Generate NiceGUI UI wiring index markdown."""
from __future__ import annotations

import argparse
from pathlib import Path

from ui_nicegui.decks import DECK_LABELS, DECK_RENDERERS


def build_nicegui_wiring_index_markdown(*, repo_root: Path) -> str:
    lines = [
        "# NiceGUI UI Wiring Index",
        "",
        "Auto-generated reference for the Streamlit → NiceGUI migration.",
        "",
        "## Evaluator choke point",
        "",
        "- Module: `ui_nicegui/evaluate.py`",
        "- Function: `ui_evaluate()` → `src.evaluator.core.Evaluator.evaluate()`",
        "",
        "## Deck registry (`DECK_RENDERERS`)",
        "",
    ]
    for deck in DECK_LABELS:
        mod = DECK_RENDERERS[deck].__module__
        fn = DECK_RENDERERS[deck].__name__
        status = "ported (Batch 1 Truth Console)" if deck == "Point Designer" else (
            "ported (Batch 2 read-only overlays)" if deck == "System Suite" else "stub"
        )
        lines.append(f"- **{deck}** — `{mod}.{fn}` ({status})")
    lines.extend([
        "",
        "## Streamlit parallel",
        "",
        "- Streamlit entry: `ui/app.py` + `run_ui.cmd` (port 8501)",
        "- NiceGUI entry: `ui_nicegui/app.py` + `run_ui_nicegui.cmd` (port 8080)",
        "",
        "## Migration orchestrator",
        "",
        "Invoke `/shams-nicegui-migration` in Cursor.",
        "",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Write ui_nicegui/UI_WIRING_INDEX.md")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    md = build_nicegui_wiring_index_markdown(repo_root=repo_root)
    if args.write:
        out = repo_root / "ui_nicegui" / "UI_WIRING_INDEX.md"
        out.write_text(md, encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(md)


if __name__ == "__main__":
    main()
