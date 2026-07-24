"""Compare verdict-first summary."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.components.workflow_cta import render_goto_setup_button
from ui_nicegui.lib.navigation import refresh_active_deck, switch_deck
from ui_nicegui.session import DesignSession


def render_compare_verdict(summary: dict | None, *, session: DesignSession | None = None) -> None:
    ui.label("Comparison verdict").classes("text-subtitle1")
    if not isinstance(summary, dict) or not summary.get("loaded"):
        empty_state(
            "Load artifacts into Slot A and Slot B to compare mechanism and margin deltas. "
            "You can load the live session from **Point Designer** or upload JSON.",
            kind="info",
        )
        with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
            if session is not None:
                render_goto_setup_button(
                    session,
                    attr="cmp_workflow_step",
                    step="1 · Load A & B",
                    label="Go to Load A & B",
                    on_refresh=refresh_active_deck,
                )
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: switch_deck("Point Designer"),
            ).props("outline color=primary")
        return
    from ui_nicegui.components.verdict_banner import verdict_banner

    va = str(summary.get("verdict_a") or "-")
    vb = str(summary.get("verdict_b") or "-")
    same = va.upper() == vb.upper()
    # "FEAS" matches INFEASIBLE — require exact FEASIBLE (or PASS) for green PASS banner.
    both_feasible = same and va.upper() in ("FEASIBLE", "PASS")
    both_infeasible = same and va.upper() in ("INFEASIBLE", "FAIL", "NO-SOLUTION", "NOSOLUTION")
    if both_feasible:
        banner = "PASS"
    elif both_infeasible:
        banner = "INFEASIBLE"
    elif va.upper() != vb.upper():
        banner = "MIXED"
    else:
        banner = va
    detail = (
        f"A: {va} (dom {summary.get('dominant_a', '-')}) · "
        f"B: {vb} (dom {summary.get('dominant_b', '-')}) · "
        f"Largest Δ: {summary.get('top_delta', '-')}"
    )
    if both_infeasible:
        detail += " · Both slots INFEASIBLE — comparison is diagnostic, not a PASS"
    elif not summary.get("feasible_a") or not summary.get("feasible_b"):
        detail += " · At least one slot INFEASIBLE — claim KPIs are diagnostic"
    verdict_banner(banner, detail=detail)
    kpi_row([
        ("Verdict A", summary.get("verdict_a", "-")),
        ("Verdict B", summary.get("verdict_b", "-")),
        ("Dominant A", summary.get("dominant_a", "-")),
        ("Dominant B", summary.get("dominant_b", "-")),
        ("Largest Δ", summary.get("top_delta", "-")),
    ])
    kpi_row([
        ("Q A", summary.get("q_a", "-")),
        ("Q B", summary.get("q_b", "-")),
        ("H98 A", summary.get("h98_a", "-")),
        ("H98 B", summary.get("h98_b", "-")),
        ("Pfus A [MW]", summary.get("pfus_a", "-")),
        ("Pfus B [MW]", summary.get("pfus_b", "-")),
    ])
    if not summary.get("feasible_a") or not summary.get("feasible_b"):
        ui.label(
            "PHYS-KPI-001: Q / H98 / Pfus shown as diagnostic residue on INFEASIBLE slots — "
            "not achieved performance claims."
        ).classes("text-caption text-orange q-mb-xs")
    with ui.row().classes("gap-2 q-mt-xs flex-wrap"):
        if summary.get("mirage_a"):
            ui.badge("MIRAGE A", color="orange").props("outline")
        if summary.get("mirage_b"):
            ui.badge("MIRAGE B", color="orange").props("outline")

    any_infeas = both_infeasible or (not summary.get("feasible_a")) or (not summary.get("feasible_b"))
    if any_infeas and session is not None:
        with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
            render_goto_setup_button(
                session,
                attr="cmp_workflow_step",
                step="3 · Constraints",
                label="Go to Constraints",
                on_refresh=refresh_active_deck,
            )
            ui.button(
                "Open Point Designer",
                icon="design_services",
                on_click=lambda: switch_deck("Point Designer"),
            ).props("outline color=primary")

    sub_rows = summary.get("subsystem_diff") or []
    changed = [r for r in sub_rows if isinstance(r, dict) and r.get("changed")]
    expert = bool(getattr(session, "cmp_expert_view", False)) if session else False
    show_sub = expert or bool(changed)
    if show_sub and sub_rows:
        with ui.expansion(
            "Subsystem pass/fail (governance groups)",
            icon="grid_view",
            value=expert or bool(changed),
        ).classes("w-full q-mt-sm"):
            ui.label(
                "Pass/fail by engineering subsystem — highlights where B regressed vs A. "
                "Subsystem pass ≠ overall FEASIBLE."
            ).classes("text-caption text-grey q-mb-xs")
            ui.table(
                columns=[
                    {"name": "subsystem", "label": "Subsystem", "field": "subsystem", "align": "left"},
                    {"name": "A", "label": "A", "field": "A"},
                    {"name": "B", "label": "B", "field": "B"},
                    {"name": "changed", "label": "Changed?", "field": "changed"},
                ],
                rows=sub_rows,
                row_key="subsystem",
            ).classes("w-full")
