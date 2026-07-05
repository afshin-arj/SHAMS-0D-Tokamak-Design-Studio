"""Cross-Code Constitutions panel."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    compare_crosscode,
    crosscode_clause_rows,
    list_crosscode_items,
)
from ui_nicegui.session import DesignSession


def render_crosscode_constitutions(session: DesignSession) -> None:
    ui.label("Cross-Code Constitutions").classes("text-h6")
    ui.label(
        "Documentation-level comparison: map external codes' declared enforcement semantics "
        "against SHAMS intent constitutions. Does not execute external codes."
    ).classes("text-caption q-mb-sm")

    items = list_crosscode_items()
    if not items:
        empty_state("No cross-code constitution records found under `benchmarks/crosscode/data/`.", kind="info")
        return

    labels = [k for k, _ in items]
    paths = {k: p for k, p in items}
    if session.pub_crosscode_code not in labels:
        session.pub_crosscode_code = labels[0]
    if session.pub_crosscode_intent not in ("research", "reactor"):
        session.pub_crosscode_intent = "research"

    code_sel = ui.select(labels, label="External code", value=session.pub_crosscode_code).classes("w-full")
    intent_sel = ui.select(
        ["research", "reactor"],
        label="SHAMS intent",
        value=session.pub_crosscode_intent,
    ).classes("w-full")

    def _run() -> None:
        session.pub_crosscode_code = str(code_sel.value)
        session.pub_crosscode_intent = str(intent_sel.value)
        try:
            comp = compare_crosscode(paths[session.pub_crosscode_code], session.pub_crosscode_intent)
            session.pub_crosscode_last = comp
            ui.notify("Comparison ready", type="positive")
            _results.refresh()
        except Exception as exc:
            ui.notify(f"Comparison failed: {exc}", type="negative")

    ui.button("Compare", icon="compare_arrows", on_click=_run).props("color=primary outline")
    _results(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    comp = session.pub_crosscode_last
    if not isinstance(comp, dict):
        return
    cc = comp.get("crosscode_constitution") or {}
    kpi_row([
        ("Unknown clauses", str(comp.get("unknown_clause_count", "-"))),
        ("Clauses total", str(len(cc.get("clauses") or {}))),
        ("Diff entries", str(len(comp.get("diff") or []))),
    ])
    notes = str(cc.get("source_notes") or "")
    if notes:
        ui.label("Notes").classes("text-subtitle2 q-mt-sm")
        ui.markdown(notes)
    citations = cc.get("citations") or []
    if citations:
        ui.label("Citations").classes("text-subtitle2 q-mt-sm")
        for c in citations:
            ui.label(f"• {c}").classes("text-caption")
    rows = crosscode_clause_rows(comp)
    if rows:
        ui.label("Clause table").classes("text-subtitle2 q-mt-sm")
        ui.table(
            columns=[
                {"name": "clause", "label": "Clause", "field": "clause", "align": "left"},
                {"name": "shams", "label": "SHAMS", "field": "shams"},
                {"name": "external", "label": "External", "field": "external"},
            ],
            rows=rows,
            row_key="clause",
        ).classes("w-full")
    with ui.expansion("Constitution diff JSON", icon="data_object").classes("w-full"):
        ui.json(comp.get("diff") or {})
    ui.button(
        "Download comparison JSON",
        icon="download",
        on_click=lambda: ui.download(
            json.dumps(comp, indent=2, default=str).encode("utf-8"),
            f"crosscode_comparison__{session.pub_crosscode_code}__{session.pub_crosscode_intent}.json",
        ),
    ).props("flat outline q-mt-sm")
