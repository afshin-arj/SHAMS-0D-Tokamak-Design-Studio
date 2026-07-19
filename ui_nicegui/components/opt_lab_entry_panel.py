"""Opt Lab entry panel — three-step certified-search hub (Phase 1.1).

Verdict-first entry that routes into existing Systems Mode / Pareto Lab /
Control Room Certified Search surfaces. Propose-only navigation; no
SearchDriver execution and no L0 mutation.
"""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.opt_lab_entry import (
    OPT_LAB_HONESTY_LINE,
    OPT_LAB_PITCH,
    OPT_LAB_ROUTES,
    OPT_LAB_STANCE_DOC,
    OPT_LAB_STEPS,
    OPT_LAB_TAGLINE,
    OPT_LAB_TITLE,
    apply_opt_lab_route_session,
)
from ui_nicegui.session import DesignSession


def _open_stance_doc(session: DesignSession) -> None:
    from ui_nicegui.lib.navigation import switch_deck

    doc_name = OPT_LAB_STANCE_DOC[1].split("/")[-1]
    session.cr_workflow_step = "2 · Constitution"
    session.cr_section = "Constitution"
    session.cr_const_tab = "Docs Library"
    session.cr_docs_sel = doc_name
    switch_deck("Control Room")
    ui.notify(f"Opened Docs Library: {doc_name}", type="info")


def _goto_route(session: DesignSession, deck: str, hook_id: str) -> None:
    from ui_nicegui.lib.navigation import switch_deck

    apply_opt_lab_route_session(session, hook_id)
    switch_deck(deck)
    ui.notify(f"Opened {deck} (certified search entry).", type="info")


def render_opt_lab_entry(session: DesignSession) -> None:
    with ui.card().classes("w-full q-mb-md").props("flat bordered"):
        ui.label(OPT_LAB_TITLE).classes("text-h6")
        ui.label(OPT_LAB_TAGLINE).classes("text-body2 q-mb-xs")
        ui.label(OPT_LAB_PITCH).classes("text-caption text-grey q-mb-sm")
        ui.label(OPT_LAB_HONESTY_LINE).classes("text-caption text-orange q-mb-sm")

        ui.label("Three steps to a certified search").classes("text-subtitle2")
        for idx, step in enumerate(OPT_LAB_STEPS, start=1):
            ui.label(f"{idx}. {step}").classes("text-caption")

        ui.separator().classes("q-my-sm")
        ui.label("Continue on an existing certified path").classes("text-subtitle2")
        ui.label(
            "Opt Lab unifies entry — it does not duplicate Systems Mode or Pareto Lab."
        ).classes("text-caption text-grey q-mb-xs")

        with ui.row().classes("w-full gap-2 flex-wrap q-mt-xs"):
            for label, deck, hook_id in OPT_LAB_ROUTES:
                ui.button(
                    label,
                    icon="arrow_forward",
                    on_click=lambda d=deck, h=hook_id: _goto_route(session, d, h),
                ).props("outline color=primary")

        with ui.row().classes("w-full gap-2 q-mt-sm"):
            ui.button(
                OPT_LAB_STANCE_DOC[0],
                icon="menu_book",
                on_click=lambda: _open_stance_doc(session),
            ).props("flat dense color=primary")
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: __import__(
                    "ui_nicegui.lib.navigation", fromlist=["switch_deck"]
                ).switch_deck("Point Designer"),
            ).props("flat dense")
