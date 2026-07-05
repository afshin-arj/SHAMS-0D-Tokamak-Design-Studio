"""SHAMS NiceGUI entrypoint — desktop/browser UI parallel to ui/app.py (Streamlit).

Launch:
  python ui_nicegui/app.py
  run_ui_nicegui.cmd   (Windows)
  ./run_ui_nicegui.sh  (Linux)
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import webbrowser

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui_nicegui.bootstrap import ensure_import_paths

ensure_import_paths()

from nicegui import ui

from ui_nicegui.lib.navigation import register_deck_change, register_helm_refresh, register_status_refresh
from ui_nicegui.decks import DECK_LABELS, DECK_RENDERERS
from ui_nicegui.components.drawer_resize import (
    inject_drawer_resize_script,
    render_drawer_resize_handle,
    toggle_helm_drawer,
)
from ui_nicegui.components.helm_console import helm_status_caption, render_helm_console
from ui_nicegui.components.helm_theme import HELM_DRAWER_CLASS, inject_helm_drawer_theme
from ui_nicegui.lib.control_room_helpers import read_version
from ui_nicegui.lib.deck_workflow import deck_workflow_caption
from ui_nicegui.session import DesignSession

# Module-level session (single-user desktop; replace with per-client storage for multi-user)
_SESSION = DesignSession()
_CONTENT: ui.column | None = None


def _switch_deck(name: str) -> None:
    _SESSION.active_deck = name
    _render_deck.refresh()
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()


@ui.refreshable
def _render_status_header(session: DesignSession) -> None:
    ui.label(helm_status_caption(session)).classes("text-caption text-grey-4 text-white")


@ui.refreshable
def _render_deck() -> None:
    global _CONTENT
    if _CONTENT is None:
        return
    _CONTENT.clear()
    with _CONTENT:
        cap = deck_workflow_caption(_SESSION.active_deck)
        if cap:
            ui.label(cap).classes("text-caption text-grey-7 q-mb-sm")
        renderer = DECK_RENDERERS.get(_SESSION.active_deck)
        if renderer is None:
            ui.label(f"Unknown deck: {_SESSION.active_deck}")
            return
        renderer(_SESSION)


@ui.page("/")
def main_page() -> None:
    global _CONTENT
    inject_helm_drawer_theme()
    inject_drawer_resize_script()
    register_deck_change(_switch_deck)
    register_helm_refresh(lambda: _helm_shell.refresh())
    register_status_refresh(lambda: _render_status_header.refresh())

    with ui.header(elevated=True).classes("bg-slate-900 text-white items-center justify-between"):
        with ui.row().classes("items-center gap-sm"):
            ui.button(
                icon="menu",
                on_click=lambda: (
                    toggle_helm_drawer(_SESSION),
                    _helm_drawer.set_value(_SESSION.helm_drawer_open),
                ),
            ).props('flat round dense title="Toggle study workflow panel (open / close)"').classes(
                "text-white"
            )
            ui.label("SHAMS").classes("text-h6 text-weight-bold")
            ui.label("Feasibility-authoritative tokamak design studio").classes("text-caption text-grey-4")
            ui.badge(f"v{read_version()}").props("outline color=grey-5")
        _render_status_header(_SESSION)

    _helm_drawer = ui.left_drawer(value=_SESSION.helm_drawer_open).classes(
        f"bg-slate-800 text-white {HELM_DRAWER_CLASS} shams-left-drawer"
    ).props("bordered").style("overflow-x: hidden;")
    _helm_drawer.bind_value(_SESSION, "helm_drawer_open")

    with _helm_drawer:
        with ui.element("div").classes("shams-drawer-body"):
            with ui.scroll_area().classes("w-full shams-helm-scroll").style(
                "height: calc(100vh - 50px);"
            ):
                with ui.column().classes(f"w-full q-pa-sm {HELM_DRAWER_CLASS} shams-helm-inner").style(
                    "min-width: 0; max-width: 100%; overflow-x: hidden;"
                ):
                    _helm_shell(_SESSION, on_deck_change=_switch_deck)
            render_drawer_resize_handle()

    with ui.column().classes("w-full p-4"):
        _CONTENT = ui.column().classes("w-full")
        _render_deck()


@ui.refreshable
def _helm_shell(session: DesignSession, *, on_deck_change) -> None:
    render_helm_console(session, on_deck_change=on_deck_change)


def _pick_port(host: str, start: int, *, span: int = 20) -> int:
    """Return the first free TCP port in [start, start+span)."""
    for port in range(start, start + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free TCP port on {host} in range {start}-{start + span - 1}")


def _open_browser(url: str, *, delay_s: float = 1.5) -> None:
    """Open default browser after the server has time to bind (Windows-safe)."""

    def _worker() -> None:
        import time

        time.sleep(delay_s)
        opened = False
        try:
            opened = webbrowser.open(url, new=2)
        except Exception as exc:
            print(f"WARNING: webbrowser.open failed: {exc}")
        if not opened and sys.platform == "win32":
            try:
                os.startfile(url)  # type: ignore[attr-defined]
                opened = True
            except Exception as exc:
                print(f"WARNING: os.startfile failed: {exc}")
        if not opened:
            print(f"Open manually in your browser: {url}")

    threading.Thread(target=_worker, daemon=True).start()


def main() -> None:
    host = os.environ.get("SHAMS_NICEGUI_HOST", "127.0.0.1")
    preferred = int(os.environ.get("SHAMS_NICEGUI_PORT", "8080"))
    port = _pick_port(host, preferred)
    url = f"http://{host}:{port}"
    if port != preferred:
        print(f"NOTE: port {preferred} is busy; using {url} instead")
    show = os.environ.get("SHAMS_NICEGUI_SHOW", "1").strip().lower() not in ("0", "false", "no")
    if show:
        _open_browser(url)
        print(f"SHAMS NiceGUI running at {url}")
        print("Browser should open automatically. Close this window to stop the server.")
    ui.run(
        host=host,
        port=port,
        reload=False,
        show=False,
        title="SHAMS — Tokamak 0-D Design Studio",
    )


if __name__ in {"__main__", "__mp_main__"}:
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback

        traceback.print_exc()
        if sys.platform == "win32" and os.environ.get("SHAMS_NICEGUI_NO_PAUSE", "") != "1":
            try:
                input("\nPress Enter to close...")
            except EOFError:
                pass
        raise
