"""Control Room — constraint cockpit and inspector."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.cr_governance_helpers import (
    constraint_detail,
    constraint_ledger_rows,
    constraint_names,
    pick_session_artifact,
)
from ui_nicegui.session import DesignSession


def render_constraints_governance(session: DesignSession) -> None:
    ui.label("Constraint governance").classes("text-subtitle2")
    ui.label("Read-only triage from the embedded constraint ledger — cockpit and single-constraint inspector.").classes(
        "text-caption q-mb-sm"
    )

    art = pick_session_artifact(session)
    if not isinstance(art, dict):
        empty_state("Load a run artifact first (**Artifacts Explorer** or evaluate in Point Designer).", kind="info")
        return

    session.cr_selected_artifact = art
    with ui.tabs().classes("w-full") as tabs:
        cockpit = ui.tab("Cockpit")
        inspector = ui.tab("Inspector")

    with ui.tab_panels(tabs, value=cockpit).classes("w-full"):
        with ui.tab_panel(cockpit):
            _cockpit(session, art)
        with ui.tab_panel(inspector):
            _inspector(session, art)


def _cockpit(session: DesignSession, art: dict) -> None:
    rows = constraint_ledger_rows(art)
    if not rows:
        ui.label("No constraint ledger in this artifact.").classes("text-warning")
        return

    failed_only = ui.checkbox("Only failed constraints", value=True)
    ui.label(f"{len(rows)} ledger entries").classes("text-caption q-mb-xs")

    @ui.refreshable
    def _table() -> None:
        view = rows
        if failed_only.value:
            view = [r for r in rows if r.get("passed") is False or r.get("failed")]
        cols = [c for c in ("name", "severity", "group", "margin_frac", "margin", "passed", "failed") if any(c in r for r in view)]
        if not cols:
            cols = list(view[0].keys())[:8] if view else ["name"]
        ui.table(
            columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
            rows=[{c: r.get(c) for c in cols} for r in view[:200]],
            row_key="name",
        ).classes("w-full")

    failed_only.on("update:model-value", lambda _: _table.refresh())
    _table()

    ledger = art.get("constraint_ledger") or {}
    top = ledger.get("top_blockers") if isinstance(ledger, dict) else None
    if isinstance(top, list) and top:
        with ui.expansion("Top blockers", icon="warning").classes("w-full"):
            ui.table(
                columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in top[0].keys()],
                rows=top,
                row_key=list(top[0].keys())[0],
            ).classes("w-full")
    fp = ledger.get("ledger_fingerprint_sha256") if isinstance(ledger, dict) else None
    if fp:
        ui.label(f"Ledger fingerprint: {fp}").classes("text-caption text-grey")


def _inspector(session: DesignSession, art: dict) -> None:
    names = constraint_names(art)
    if not names:
        ui.label("No constraints found in artifact.").classes("text-warning")
        return
    if session.cr_constraint_inspect_name not in names:
        session.cr_constraint_inspect_name = names[0]
    sel = ui.select(
        names,
        label="Constraint",
        value=session.cr_constraint_inspect_name,
        on_change=lambda e: setattr(session, "cr_constraint_inspect_name", str(e.value)),
    ).classes("w-full q-mb-sm")

    detail = constraint_detail(art, str(sel.value or names[0]))
    if not detail:
        ui.label("No detail available for this constraint.").classes("text-grey")
        return

    for key in ("name", "severity", "group", "passed", "failed", "margin", "margin_frac", "residual", "meaning"):
        if key in detail and detail[key] is not None:
            ui.label(f"{key}: {detail[key]}").classes("text-body2")

    with ui.expansion("Full constraint record", icon="data_object").classes("w-full"):
        ui.json(detail)
