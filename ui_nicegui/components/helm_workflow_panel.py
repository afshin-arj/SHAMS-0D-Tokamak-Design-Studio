"""Helm Console — study workflow compass (phase strip, actions, next step)."""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from ui_nicegui.lib.deck_workflow import DECK_WORKFLOW_STEP, deck_nav_short_label
from ui_nicegui.lib.helm_workflow_guide import (
    DECK_NOW_ACTIONS,
    WORKFLOW_PHASES,
    deck_phase,
    phase_completion,
    phase_title,
    suggest_next_deck,
    workflow_progress,
)
from ui_nicegui.session import DesignSession


def render_workflow_compass(
    session: DesignSession,
    *,
    on_deck_change: Callable[[str], None],
) -> None:
    active = session.active_deck
    step = DECK_WORKFLOW_STEP.get(active, 0)
    phase = deck_phase(active)
    progress = workflow_progress(session)

    ui.label("Study workflow").classes("text-subtitle2 text-weight-bold q-mb-xs")
    ui.label(f"Phase {phase} · {phase_title(phase)} · deck {step}/10").classes("text-caption q-mb-sm")

    with ui.row().classes("w-full gap-1 q-mb-sm flex-wrap"):
        for i, (title, _) in enumerate(WORKFLOW_PHASES, start=1):
            done = phase_completion(i, progress)
            current = i == phase
            cls = "helm-phase-pill"
            if current:
                cls += " helm-phase-active"
            elif done:
                cls += " helm-phase-done"
            ui.html(f'<span class="{cls}" title="{title}">{i}</span>')

    ui.label(active).classes("text-body2 text-weight-bold")
    actions = DECK_NOW_ACTIONS.get(active, [])
    if actions:
        ui.markdown("**Do now:**\n" + "\n".join(f"- {a}" for a in actions[:3])).classes(
            "text-caption helm-deck-hint q-mb-sm"
        )

    nxt, reason = suggest_next_deck(session, active)
    if reason:
        ui.label(reason).classes("text-caption text-grey q-mb-xs")
    if nxt and nxt != active:

        def _go_next() -> None:
            on_deck_change(nxt)
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status

            refresh_helm()
            refresh_status()

        ui.button(
            f"Next → {deck_nav_short_label(nxt)}",
            on_click=_go_next,
        ).props("outline dense color=primary").classes("w-full q-mb-sm")


def render_deck_navigation(
    session: DesignSession,
    *,
    groups: list[tuple[str, str, list[str]]],
    on_deck_change: Callable[[str], None],
) -> None:
    ui.label("Decks").classes("text-subtitle2 q-mb-xs")

    def _go(deck: str) -> None:
        on_deck_change(deck)
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_helm()
        refresh_status()

    for group_title, caption, decks in groups:
        active_group = session.active_deck in decks
        # Active phase stays pinned open — re-clicking the header must not collapse
        # the deck list (QA harness / accidental toggle). Inactive phases stay expandable.
        if active_group:
            with ui.column().classes(
                "w-full helm-nav-group helm-nav-group-active overflow-hidden q-mb-xs"
            ).props("data-testid=helm-nav-group-active"):
                ui.label(group_title).classes("text-body2 text-weight-medium")
                ui.label(caption).classes("text-caption q-mb-xs")
                _render_group_deck_buttons(decks, session, _go)
        else:
            with ui.expansion(group_title, icon="chevron_right", value=False).classes(
                "w-full helm-nav-group overflow-hidden"
            ).props("data-testid=helm-nav-group"):
                ui.label(caption).classes("text-caption q-mb-xs")
                _render_group_deck_buttons(decks, session, _go)


def _render_group_deck_buttons(
    decks: list[str],
    session: DesignSession,
    go: Callable[[str], None],
) -> None:
    for deck in decks:
        active = deck == session.active_deck
        label = deck_nav_short_label(deck)
        btn = ui.button(label, on_click=lambda d=deck: go(d)).props(
            "flat align=left dense no-caps"
        ).classes("w-full helm-deck-btn")
        if active:
            btn.classes(add="helm-deck-btn-active")
