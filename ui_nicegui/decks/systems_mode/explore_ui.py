"""Systems Mode — Explore / feasible search (Phase 12)."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.lib.systems_precheck import build_targets_and_variables
from ui_nicegui.lib.systems_workflow_helpers import append_run_card, run_feasible_search, systems_run_payload
from ui_nicegui.session import DesignSession


def render_explore_panel(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Feasible design search (top-K)").classes("text-subtitle1")
    ui.label(
        "Budgeted random walk in declared bounds — generates top-K candidates "
        "for compare/apply. Reactor intent keeps feasible-only candidates."
    ).classes("text-caption q-mb-sm")

    base = session.build_point_inputs()
    _, variables = build_targets_and_variables(session, base)
    if not variables:
        ui.label("Configure iteration variables in Setup first.").classes("text-orange")
        return

    with ui.row().classes("gap-4 flex-wrap"):
        ui.number(
            "Budget",
            value=session.systems_fs_budget,
            min=20,
            max=3000,
            on_change=lambda e: setattr(session, "systems_fs_budget", int(e.value or 150)),
        ).classes("w-24")
        ui.number(
            "Top-K",
            value=session.systems_fs_topk,
            min=1,
            max=50,
            on_change=lambda e: setattr(session, "systems_fs_topk", int(e.value or 8)),
        ).classes("w-20")
        ui.number(
            "Radius",
            value=session.systems_fs_radius,
            min=0.05,
            max=1.0,
            step=0.05,
            on_change=lambda e: setattr(session, "systems_fs_radius", float(e.value or 0.25)),
        ).classes("w-24")
        ui.number(
            "Seed",
            value=session.systems_fs_seed,
            min=0,
            max=999999,
            on_change=lambda e: setattr(session, "systems_fs_seed", int(e.value or 2026)),
        ).classes("w-24")

    async def _run() -> None:
        if session.systems_fs_running:
            ui.notify("Search already running", type="warning")
            return
        session.systems_fs_running = True
        ui.notify("Running feasible search…", type="info")
        try:
            reactor = "reactor" in str(session.design_intent).lower()
            rep = await run.io_bound(
                run_feasible_search,
                session.build_point_inputs(),
                variables,
                rng_seed=session.systems_fs_seed,
                budget=session.systems_fs_budget,
                topk=session.systems_fs_topk,
                radius=session.systems_fs_radius,
                reactor_intent=reactor,
            )
            session.systems_feasible_search_last = rep
            append_run_card(
                session,
                kind="FeasibleSearch",
                settings={"budget": session.systems_fs_budget, "topk": session.systems_fs_topk},
                outcome={"ok": bool(rep.get("ok")), "reason": str(rep.get("reason", ""))},
                payload=systems_run_payload(session),
            )
            ui.notify(
                f"Search complete — {len(rep.get('candidates') or [])} candidates",
                type="positive" if rep.get("ok") else "warning",
            )
            _results.refresh()
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Search failed: {exc}", type="negative")
        finally:
            session.systems_fs_running = False

    ui.button("Run feasible search", icon="travel_explore", on_click=_run).props("outline q-mb-sm")
    _results(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    rep = session.systems_feasible_search_last
    if not isinstance(rep, dict):
        return
    ui.label(f"Search: {rep.get('reason', '-')} | candidates={len(rep.get('candidates') or [])}").classes(
        "text-body2"
    )
    rows = []
    for i, c in enumerate(rep.get("candidates") or []):
        if not isinstance(c, dict):
            continue
        h = c.get("headline") or {}
        rows.append(
            {
                "rank": i + 1,
                "feasible": c.get("feasible"),
                "Q": h.get("Q"),
                "H98": h.get("H98"),
                "P_net": h.get("P_net"),
                "V": c.get("V"),
            }
        )
    if rows:
        ui.table(
            columns=[
                {"name": "rank", "label": "#", "field": "rank"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
                {"name": "Q", "label": "Q", "field": "Q"},
                {"name": "H98", "label": "H98", "field": "H98"},
                {"name": "P_net", "label": "P_net", "field": "P_net"},
                {"name": "V", "label": "V", "field": "V"},
            ],
            rows=rows,
            row_key="rank",
        ).classes("w-full")
