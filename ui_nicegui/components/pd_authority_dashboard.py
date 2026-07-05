"""Compact authority overlay status board for Point Designer Configure."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.pd_authority_toggles import (
    AUTHORITY_OVERLAY_TOGGLES,
    AUTHORITY_TOGGLE_KEYS,
    count_enabled,
    default_overlay_bool,
    reactor_intent_hint,
)
from ui_nicegui.session import DesignSession


def render_authority_status_board(session: DesignSession, *, compact: bool = False) -> None:
    """Quick authority overlay toggles — governance only, frozen truth unchanged."""
    overlay = session.overlay
    for key in AUTHORITY_TOGGLE_KEYS:
        overlay.setdefault(key, default_overlay_bool(overlay, key, session.design_intent))

    enabled, total = count_enabled(overlay)
    hint = reactor_intent_hint(session.design_intent)

    if compact:
        color = "positive" if enabled >= total // 2 else "orange"
        ui.badge(f"Authority overlays: {enabled}/{total} ON", color=color).props("outline")
        if hint:
            ui.label(hint).classes("text-caption text-grey")
        return

    with ui.expansion(
        f"Authority status board ({enabled}/{total} modules ON)",
        icon="verified_user",
    ).classes("w-full q-mb-sm"):
        ui.label("Governance overlays only — frozen truth equations unchanged.").classes(
            "text-caption q-mb-xs"
        )
        if hint:
            ui.label(hint).classes("text-caption text-info q-mb-sm")

        cols_per_row = 3
        for row_start in range(0, len(AUTHORITY_OVERLAY_TOGGLES), cols_per_row):
            chunk = AUTHORITY_OVERLAY_TOGGLES[row_start : row_start + cols_per_row]
            with ui.row().classes("w-full gap-4 flex-wrap"):
                for field, tag, tip in chunk:
                    with ui.column().classes("gap-0"):
                        ui.checkbox(
                            tag,
                            value=bool(overlay.get(field, False)),
                            on_change=lambda e, k=field: overlay.__setitem__(k, bool(e.value)),
                        ).props(f'title="{tip}"')
                        ui.label(tip).classes("text-caption text-grey q-pl-lg")

        if bool(overlay.get("include_authority_dominance_v402", True)):
            ui.label("Dominance reference thresholds are in Design governance above.").classes(
                "text-caption q-mt-sm"
            )
