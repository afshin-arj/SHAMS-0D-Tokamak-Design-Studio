"""Contract Studio panel — NiceGUI."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pub_benchmark_extended_helpers import (
    contract_bundle_zip,
    contract_structural_diff,
    load_contract,
    validate_contracts,
)
from ui_nicegui.session import DesignSession


def render_contract_studio_panel(session: DesignSession) -> None:
    ui.label("Contract Studio").classes("text-h6")
    ui.label("Validate and export governance contracts (read-only).").classes("text-caption q-mb-sm")

    try:
        recs, summary = validate_contracts()
    except Exception as exc:
        ui.label(f"Contract validation unavailable: {exc}").classes("text-negative")
        return

    kpi_row([
        ("Contracts", str(summary.get("n_contracts", 0))),
        ("OK", str(summary.get("n_ok", 0))),
        ("Errors", str(summary.get("n_errors", 0))),
        ("Warnings", str(summary.get("n_warnings", 0))),
    ])
    fp = str(summary.get("contracts_fingerprint_sha256") or "")[:12]
    if fp:
        ui.label(f"Fingerprint SHA-256: {fp}…").classes("text-caption")

    names = [r.name for r in recs]
    if not names:
        ui.label("No contracts found under `contracts/`.").classes("text-warning")
        return

    if session.pub_contract_sel_a not in names:
        session.pub_contract_sel_a = names[0]
    sel_a = ui.select(names, label="Contract A", value=session.pub_contract_sel_a).classes("w-full")
    sel_b = ui.select(["(none)"] + names, label="Contract B (optional diff)", value=session.pub_contract_sel_b or "(none)").classes(
        "w-full"
    )

    def _refresh() -> None:
        session.pub_contract_sel_a = str(sel_a.value)
        session.pub_contract_sel_b = str(sel_b.value)
        _detail.refresh()

    sel_a.on("update:model-value", lambda: _refresh())
    sel_b.on("update:model-value", lambda: _refresh())
    _detail(session, recs)
    ui.button(
        "Download contracts bundle ZIP",
        icon="download",
        on_click=lambda: ui.download(contract_bundle_zip(), "shams_contracts_bundle.zip"),
    ).props("outline q-mt-md")


@ui.refreshable
def _detail(session: DesignSession, recs) -> None:
    obj_a, errs_a = load_contract(session.pub_contract_sel_a)
    if errs_a:
        ui.label(f"Failed to load A: {errs_a}").classes("text-negative")
        return
    if obj_a is not None:
        with ui.expansion(f"{session.pub_contract_sel_a}", icon="description").classes("w-full"):
            ui.json(obj_a)
    sel_b = session.pub_contract_sel_b or "(none)"
    if sel_b != "(none)":
        obj_b, errs_b = load_contract(sel_b)
        if obj_b is not None and obj_a is not None:
            with ui.expansion("Structural diff (keys)", icon="difference").classes("w-full"):
                ui.json(contract_structural_diff(obj_a, obj_b))
        elif errs_b:
            ui.label(f"Failed to load B: {errs_b}").classes("text-negative")

    rows = [
        {
            "name": r.name,
            "ok": "yes" if r.ok else "no",
            "sha256": str(r.sha256)[:12] + "…",
            "errors": len(r.errors),
            "warnings": len(r.warnings),
        }
        for r in recs
    ]
    with ui.expansion("Contracts table", icon="table_chart").classes("w-full q-mt-sm"):
        ui.table(
            columns=[
                {"name": "name", "label": "Name", "field": "name", "align": "left"},
                {"name": "ok", "label": "OK", "field": "ok"},
                {"name": "sha256", "label": "SHA-256", "field": "sha256"},
                {"name": "errors", "label": "Errors", "field": "errors"},
                {"name": "warnings", "label": "Warnings", "field": "warnings"},
            ],
            rows=rows,
            row_key="name",
        ).classes("w-full")
