"""Small workflow navigation buttons after empty states."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.session import DesignSession


def goto_workflow_step(
    session: DesignSession,
    attr: str,
    step: str,
    *,
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    setattr(session, attr, step)
    if on_refresh is not None:
        on_refresh()


def render_goto_setup_button(
    session: DesignSession,
    *,
    attr: str,
    step: str = "1 · Setup & Run",
    label: str = "Go to Setup & Run",
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    ui.button(
        label,
        icon="settings",
        on_click=lambda: goto_workflow_step(session, attr, step, on_refresh=on_refresh),
    ).props("outline").classes("q-mt-sm")
