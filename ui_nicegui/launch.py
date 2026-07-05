"""Robust NiceGUI launcher — keeps terminal open on Windows and opens the browser explicitly."""
from __future__ import annotations

import os
import sys
import traceback

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _pause_on_error() -> None:
    if os.environ.get("SHAMS_NICEGUI_NO_PAUSE", "").strip().lower() in ("1", "true", "yes"):
        return
    if sys.platform == "win32":
        try:
            input("\nPress Enter to close this window...")
        except EOFError:
            pass


def main() -> int:
    try:
        from ui_nicegui.app import main as run_app

        run_app()
        return 0
    except KeyboardInterrupt:
        print("\nNiceGUI stopped by user.")
        return 0
    except Exception:
        print("\nERROR: NiceGUI failed to start:\n", file=sys.stderr)
        traceback.print_exc()
        _pause_on_error()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
