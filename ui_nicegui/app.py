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

from nicegui import app, ui

from ui_nicegui.lib.navigation import (
    register_deck_change,
    register_deck_refresh,
    register_helm_refresh,
    register_helm_settings_refresh,
    register_status_refresh,
)
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

# Legacy burst-timer bookkeeping (NAV-IMMEDIATE-001 retired coalesce). Kept only so
# any in-flight timer from an older session/build can still be cancelled safely.
_pending_deck_remount: dict[str, object] = {"timer": None, "name": None, "coalesced": False, "gen": 0}


def _cancel_pending_deck_remount() -> None:
    timer = _pending_deck_remount.get("timer")
    if timer is not None:
        try:
            timer.cancel()  # type: ignore[union-attr]
        except Exception:
            pass
        _pending_deck_remount["timer"] = None
    _pending_deck_remount["coalesced"] = False


def _remount_active_deck() -> None:
    """Remount the current active deck body (NAV-001 refreshable slot)."""
    _render_deck.refresh()


def _sync_helm_chrome() -> None:
    """Refresh Helm nav + status caption — always call alongside a body remount.

    NAV-CHROME-001: Helm chrome and the visible deck body must never disagree.
    Both refresh only via ``_remount_and_sync_chrome``.
    """
    from ui_nicegui.lib.navigation import refresh_helm, refresh_status

    refresh_helm()
    refresh_status()


def _remount_and_sync_chrome() -> None:
    """Remount the deck body and refresh Helm chrome atomically (NAV-CHROME-001)."""
    _remount_active_deck()
    _sync_helm_chrome()


def _apply_deck_switch(name: str, *, force: bool = False) -> None:
    """Immediate full switch: session + DSG + remount + Helm/status (NAV-001)."""
    same = name == _SESSION.active_deck
    if same and not force:
        return
    if not same:
        _SESSION.active_deck = name
    from ui_nicegui.lib.deck_dsg_hooks import apply_deck_dsg_context, deck_edge_kind_for

    apply_deck_dsg_context(_SESSION, deck_edge_kind_for(name))
    _remount_and_sync_chrome()


def _switch_deck(name: str, *, force: bool = False) -> None:
    """Navigate to a deck and remount the main panel when the target changes.

    NAV-001: deck body must live in ``_render_deck``'s refreshable slot (not a
    sibling ``_CONTENT`` column). Writing into an external container while the
    refreshable slot stayed empty left Helm/`active_deck` updated and the
    previous deck DOM still visible after handoffs and nav clicks.

    NAV-IMMEDIATE-001: every target change remounts body + Helm chrome
    immediately. Debounced coalesce was removed — mid-burst clicks previously
    left the body on the prior deck for up to ~60 ms (chrome either ahead or
    also lagged), which users experienced as deck-switch bugs / delay.

    Same-deck clicks no-op unless ``force=True`` (handoffs that mutate session).
    Force always cancels any leftover pending timer and bumps generation
    (NAV-GEN-001) so stale callbacks cannot remount after recovery/handoff.
    """
    same = name == _SESSION.active_deck
    if same and not force:
        return

    _cancel_pending_deck_remount()
    if force:
        _pending_deck_remount["gen"] = int(_pending_deck_remount.get("gen") or 0) + 1

    _apply_deck_switch(name, force=force)


@ui.refreshable
def _render_status_header(session: DesignSession) -> None:
    ui.label(helm_status_caption(session)).classes("text-caption text-grey-4 text-white")


def _recover_to_point_designer() -> None:
    """Error-boundary recovery CTA — must go through ``_switch_deck`` (NAV-GEN-001).

    Applying the deck switch directly (bypassing the public entry point, as
    this used to) skipped the generation-token bump / pending-timer cancel
    that force switches normally get. A rapid-click burst still in flight
    when a deck crashed could then fire its stale trailing remount *after*
    recovery, coalescing back to whatever deck that burst was originally
    headed to instead of staying on Point Designer, or silently swallowing
    the next ordinary nav click into that stale burst.
    """
    _switch_deck("Point Designer", force=True)


@ui.refreshable
def _render_deck() -> None:
    """Render active deck into this refreshable's own slot (authoritative remount target).

    UI-DECK-CRASH-001: a deck render raising mid-way used to leave a half-built,
    unexplained page with no recovery path other than the (still-live) Helm nav —
    confusing for an expert diagnosing their own inputs. Any renderer exception is
    now caught here, logged, and surfaced as an explicit recoverable card instead
    of a silent/partial page (SHAMS error-handling law: explicit, no silent failure).
    """
    cap = deck_workflow_caption(_SESSION.active_deck)
    if cap:
        ui.label(cap).classes("text-caption text-grey-7 q-mb-sm")
    renderer = DECK_RENDERERS.get(_SESSION.active_deck)
    if renderer is None:
        ui.label(f"Unknown deck: {_SESSION.active_deck!r} — returning to Point Designer.").classes(
            "text-negative"
        )
        ui.button(
            "Open Point Designer", icon="design_services", on_click=_recover_to_point_designer
        ).props("outline color=primary").classes("q-mt-sm")
        return
    try:
        renderer(_SESSION)
    except Exception as exc:  # noqa: BLE001 - deck-render error boundary, see docstring
        import traceback

        traceback.print_exc()
        with ui.card().classes("w-full p-4 bg-red-1"):
            ui.label(f"{_SESSION.active_deck} failed to render").classes("text-h6 text-negative")
            ui.label(f"{type(exc).__name__}: {exc}").classes("text-body2 text-negative")
            ui.label(
                "This is a UI-layer fault (not a physics result) — no evaluation output was lost. "
                "Try again, or go back to Point Designer."
            ).classes("text-caption text-grey")
            with ui.row().classes("gap-2 q-mt-sm"):
                ui.button("Retry this deck", icon="refresh", on_click=_render_deck.refresh).props(
                    "outline dense"
                )
                ui.button(
                    "Open Point Designer",
                    icon="design_services",
                    on_click=_recover_to_point_designer,
                ).props("outline dense color=primary")
            with ui.expansion("Traceback (for bug report)", icon="bug_report").classes("w-full q-mt-sm"):
                ui.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), language="text")


@ui.page("/")
def main_page() -> None:
    inject_helm_drawer_theme()
    inject_drawer_resize_script()
    register_deck_change(_switch_deck)
    register_deck_refresh(lambda: _render_deck.refresh())
    from ui_nicegui.components.helm_console import refresh_helm_navigation, refresh_helm_settings_panel

    register_helm_refresh(refresh_helm_navigation)
    register_helm_settings_refresh(refresh_helm_settings_panel)
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
            _ver = read_version()
            ui.badge(_ver if _ver.startswith("v") else f"v{_ver}").props("outline color=grey-5")
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
                    from ui_nicegui.components.helm_console import render_helm_console

                    render_helm_console(_SESSION, on_deck_change=_switch_deck)
            render_drawer_resize_handle()

    with ui.column().classes("w-full p-4"):
        # Desktop single-session notice — shared module-level DesignSession (NAV multi-tab).
        ui.label(
            "Desktop single-session: open only one browser tab. A second tab shares the same "
            "machine state and can overwrite evaluations or fight over the active deck."
        ).classes("text-caption text-orange q-mb-sm")
        # Deck body must be the refreshable slot itself — see _switch_deck / NAV-001.
        _render_deck()


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


def _notify_on_uncaught_exception(exc: Exception) -> None:
    """App-wide safety net: NiceGUI's default handler only logs server-side.

    Event handlers outside a deck's own render pass (Helm console toggles, async
    run callbacks, etc.) had no user-visible failure signal at all — a silent
    failure the SHAMS error-handling law forbids. This never touches physics
    state; it only ensures the operator sees that *something* failed.
    """
    import traceback

    traceback.print_exc()
    try:
        ui.notify(f"Unexpected UI error: {type(exc).__name__}: {exc}", type="negative", timeout=8000)
    except Exception:
        pass


def main() -> None:
    app.on_exception(_notify_on_uncaught_exception)
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
