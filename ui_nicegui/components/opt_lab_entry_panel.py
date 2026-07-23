"""Opt Lab entry panel — three-step certified-search hub (Phase 1.1).

Verdict-first entry that routes into existing Systems Mode / Pareto Lab /
Control Room Certified Search surfaces. Propose-only navigation; no
SearchDriver execution and no L0 mutation.
"""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.certified_front_viewer_panel import render_certified_front_viewer
from ui_nicegui.components.opt_lab_warm_start_panel import render_champion_warm_start
from ui_nicegui.lib.opt_lab_entry import (
    OPT_LAB_CERTIFIED_FRONT_NOTE,
    OPT_LAB_HONESTY_LINE,
    OPT_LAB_NSGA2_HOOK_NOTE,
    OPT_LAB_PITCH,
    OPT_LAB_ROUTES,
    OPT_LAB_SLSQP_HOOK_NOTE,
    OPT_LAB_STANCE_DOC,
    OPT_LAB_STEPS,
    OPT_LAB_SURROGATE_HOOK_NOTE,
    OPT_LAB_TAGLINE,
    OPT_LAB_TITLE,
    apply_opt_lab_route_session,
    opt_lab_last_run_stamp_summary,
)
from ui_nicegui.session import DesignSession


def _open_stance_doc(session: DesignSession) -> None:
    from ui_nicegui.lib.navigation import switch_deck

    doc_name = OPT_LAB_STANCE_DOC[1].split("/")[-1]
    session.cr_workflow_step = "2 · Constitution"
    session.cr_section = "Constitution"
    session.cr_const_tab = "Docs Library"
    session.cr_docs_sel = doc_name
    switch_deck("Control Room", force=True)
    ui.notify(f"Opened Docs Library: {doc_name}", type="info")


def _goto_route(session: DesignSession, deck: str, hook_id: str) -> None:
    from ui_nicegui.lib.navigation import switch_deck

    apply_opt_lab_route_session(session, hook_id)
    # force=True: route mutates session (hook + tab seeds) before leave — remount target.
    switch_deck(deck, force=True)
    ui.notify(f"Opened {deck} (certified search entry).", type="info")


def render_opt_lab_entry(session: DesignSession) -> None:
    with ui.card().classes("w-full q-mb-md").props("flat bordered"):
        ui.label(OPT_LAB_TITLE).classes("text-h6")
        ui.label(OPT_LAB_TAGLINE).classes("text-body2 q-mb-xs")
        ui.label(OPT_LAB_PITCH).classes("text-caption text-grey q-mb-sm")
        ui.label(OPT_LAB_HONESTY_LINE).classes("text-caption text-orange q-mb-sm")
        ui.label(opt_lab_last_run_stamp_summary(session)).classes(
            "text-caption text-grey q-mb-sm"
        )

        render_champion_warm_start(session)

        render_certified_front_viewer(
            session,
            compact=False,
            show_handoff_to_pareto=True,
            show_handoff_to_opt_lab=False,
        )

        ui.label("Three steps to a certified search").classes("text-subtitle2")
        for idx, step in enumerate(OPT_LAB_STEPS, start=1):
            ui.label(f"{idx}. {step}").classes("text-caption")

        ui.label(OPT_LAB_SLSQP_HOOK_NOTE).classes("text-caption text-grey q-mt-sm")
        ui.label(OPT_LAB_NSGA2_HOOK_NOTE).classes("text-caption text-grey q-mt-xs")
        ui.label(OPT_LAB_CERTIFIED_FRONT_NOTE).classes("text-caption text-grey q-mt-xs")
        ui.label(OPT_LAB_SURROGATE_HOOK_NOTE).classes("text-caption text-grey q-mt-xs")

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

        ui.separator().classes("q-my-sm")
        ui.label("Promote certified best → Point Designer").classes("text-subtitle2")
        ui.label(
            "Seeds Point Designer from this session's Certified Search best (preferred) "
            "or Pareto front #0 — prior KPIs cleared; Evaluate Point to re-certify."
        ).classes("text-caption text-grey q-mb-xs")

        def _promote_best() -> None:
            from ui_nicegui.lib.opt_lab_promote import promote_opt_lab_best_to_point_designer
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status

            n, src = promote_opt_lab_best_to_point_designer(session)
            if n <= 0:
                ui.notify(
                    "No Certified Search best or Pareto front yet — run a search path first.",
                    type="warning",
                )
                return
            refresh_helm()
            refresh_status()
            navigate_to_point_designer(session)
            ui.notify(
                f"Promoted {n} fields from {src} → Point Designer — "
                "prior KPIs cleared; Evaluate Point to re-certify.",
                type="warning",
            )

        with ui.row().classes("w-full gap-2 q-mt-xs flex-wrap"):
            ui.button(
                "Promote certified best → Point Designer",
                icon="upload",
                on_click=_promote_best,
            ).props("outline color=primary data-testid=opt-lab-promote-best")
            ui.button(
                OPT_LAB_STANCE_DOC[0],
                icon="menu_book",
                on_click=lambda: _open_stance_doc(session),
            ).props("flat dense color=primary")
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: __import__(
                    "ui_nicegui.lib.pd_handoff", fromlist=["navigate_to_point_designer"]
                ).navigate_to_point_designer(session),
            ).props("flat dense")
