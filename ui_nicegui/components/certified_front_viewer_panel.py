"""NiceGUI certified-front viewer panel — Opt Lab ↔ Pareto Lab (Phase 3.3).

Shared verdict-first strip: VERIFIED/REJECTED counts, honesty, handoff buttons.
Does not duplicate Pareto Lab explore/interpret decks.
"""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.certified_front_viewer import (
    CERTIFIED_FRONT_EMPTY,
    CERTIFIED_FRONT_HONESTY,
    CERTIFIED_FRONT_TAGLINE,
    CERTIFIED_FRONT_TITLE,
    HANDOFF_TO_OPT_LAB_LABEL,
    HANDOFF_TO_PARETO_LABEL,
    apply_handoff_to_opt_lab,
    apply_handoff_to_pareto,
    atlas_reject_hint,
    format_front_caption,
    get_certified_front,
    sync_certified_front_from_session,
)
from ui_nicegui.session import DesignSession


def render_certified_front_viewer(
    session: DesignSession,
    *,
    compact: bool = False,
    show_handoff_to_pareto: bool = True,
    show_handoff_to_opt_lab: bool = False,
    default_open: Optional[bool] = None,
    on_navigated: Optional[Callable[[], None]] = None,
) -> None:
    """Render the shared certified-front viewer (expansion when compact)."""
    summary = sync_certified_front_from_session(session) or get_certified_front(session)
    open_default = (
        bool(default_open)
        if default_open is not None
        else bool(getattr(session, "opt_lab_show_certified_front", False) or summary)
    )

    def _goto_pareto() -> None:
        from ui_nicegui.lib.navigation import switch_deck

        apply_handoff_to_pareto(session)
        switch_deck("Pareto Lab", force=True)
        ui.notify("Opened Pareto Lab on certified-front Interpret view.", type="info")
        if on_navigated:
            on_navigated()

    def _goto_opt_lab() -> None:
        from ui_nicegui.lib.navigation import switch_deck

        apply_handoff_to_opt_lab(session)
        switch_deck("Opt Lab", force=True)
        ui.notify("Opened Opt Lab certified-front viewer.", type="info")
        if on_navigated:
            on_navigated()

    body_cls = "w-full q-mb-md"
    if compact:
        with ui.expansion(
            CERTIFIED_FRONT_TITLE,
            icon="verified",
            value=open_default,
        ).classes(body_cls):
            _render_body(
                summary,
                show_handoff_to_pareto=show_handoff_to_pareto,
                show_handoff_to_opt_lab=show_handoff_to_opt_lab,
                on_pareto=_goto_pareto,
                on_opt_lab=_goto_opt_lab,
            )
    else:
        with ui.card().classes(body_cls).props("flat bordered"):
            ui.label(CERTIFIED_FRONT_TITLE).classes("text-subtitle1")
            _render_body(
                summary,
                show_handoff_to_pareto=show_handoff_to_pareto,
                show_handoff_to_opt_lab=show_handoff_to_opt_lab,
                on_pareto=_goto_pareto,
                on_opt_lab=_goto_opt_lab,
            )


def _render_body(
    summary,
    *,
    show_handoff_to_pareto: bool,
    show_handoff_to_opt_lab: bool,
    on_pareto,
    on_opt_lab,
) -> None:
    ui.label(CERTIFIED_FRONT_TAGLINE).classes("text-caption text-grey q-mb-xs")
    ui.label(CERTIFIED_FRONT_HONESTY).classes("text-caption text-orange q-mb-sm")
    ui.label(format_front_caption(summary)).classes("text-body2 q-mb-xs")
    ui.label(atlas_reject_hint(summary)).classes("text-caption text-grey q-mb-sm")
    if summary is None:
        ui.label(CERTIFIED_FRONT_EMPTY).classes("text-caption text-grey")
    bridge = ""
    if isinstance(summary, dict):
        bridge = str(summary.get("extopt_bridge_note") or "").strip()
    if bridge:
        ui.label(bridge).classes("text-caption text-grey q-mb-sm")

    with ui.row().classes("w-full gap-2 flex-wrap"):
        if show_handoff_to_pareto:
            ui.button(
                HANDOFF_TO_PARETO_LABEL,
                icon="arrow_forward",
                on_click=on_pareto,
            ).props("outline color=primary dense")
        if show_handoff_to_opt_lab:
            ui.button(
                HANDOFF_TO_OPT_LAB_LABEL,
                icon="science",
                on_click=on_opt_lab,
            ).props("outline color=primary dense")
