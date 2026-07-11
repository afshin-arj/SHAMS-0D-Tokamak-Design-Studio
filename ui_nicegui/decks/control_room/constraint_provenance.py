"""Control Room — constraint provenance drill-down."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.cr_chronicle_helpers import constraint_provenance_rows
from ui_nicegui.lib.cr_governance_helpers import pick_session_artifact
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def _render_constraint_detail(pick: dict, name: str) -> None:
    ui.label(f"Selected: {name}").classes("text-subtitle2")
    fp_keys = ("fingerprint", "provenance_fingerprint", "constraint_fingerprint_sha256")
    fp_lines = [f"{k}: {pick.get(k)}" for k in fp_keys if k in pick and pick.get(k) is not None]
    if fp_lines:
        ui.label("Fingerprint fields").classes("text-caption text-grey")
        ui.code("\n".join(fp_lines))
    for key in (
        "meaning",
        "provenance",
        "authority_tier",
        "validity_domain",
        "best_knobs",
        "dominant_inputs",
        "mechanism_group",
    ):
        if key in pick and pick[key] is not None:
            ui.label(f"{key}: {pick[key]}").classes("text-body2")
    with ui.expansion("Full constraint record", icon="data_object").classes("w-full"):
        render_json_blob(pick)


def render_constraint_provenance(session: DesignSession) -> None:
    ui.label("Constraint Provenance Drill-Down").classes("text-subtitle2")
    ui.label(
        "Inspect constraint definitions, fingerprints, and maturity/provenance metadata embedded in the artifact."
    ).classes("text-caption q-mb-sm")

    art = pick_session_artifact(session)
    if not isinstance(art, dict):
        empty_state("Load a run artifact (**Artifacts Explorer**) or evaluate in Point Designer.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )
        return

    session.cr_selected_artifact = art
    rows = constraint_provenance_rows(art)
    if not rows:
        ui.label("No constraints list found in this artifact.").classes("text-warning")
        return

    cols = [
        c
        for c in (
            "group",
            "name",
            "failed",
            "severity",
            "value",
            "limit",
            "margin",
            "margin_frac",
            "units",
            "fingerprint",
            "provenance_fingerprint",
            "maturity",
        )
        if any(c in r for r in rows)
    ]
    ui.table(
        columns=[{"name": c, "label": c, "field": c, "align": "left"} for c in cols],
        rows=[{c: r.get(c) for c in cols} for r in rows[:200]],
        row_key="name",
    ).classes("w-full q-mb-sm")

    names = [str(r.get("name") or f"constraint_{i}") for i, r in enumerate(rows)]
    if session.cr_cprov_sel not in names:
        session.cr_cprov_sel = names[0]

    cons = art.get("constraints") if isinstance(art.get("constraints"), list) else []
    detail_panel = ui.column().classes("w-full")

    def _on_sel(e) -> None:
        session.cr_cprov_sel = str(e.value)
        pick = next(
            (c for c in cons if isinstance(c, dict) and str(c.get("name", c.get("id"))) == session.cr_cprov_sel),
            None,
        )
        detail_panel.clear()
        with detail_panel:
            if isinstance(pick, dict):
                _render_constraint_detail(pick, session.cr_cprov_sel)

    ui.select(
        names,
        label="Select constraint",
        value=session.cr_cprov_sel,
        on_change=_on_sel,
    ).classes("w-full q-mb-sm")

    pick0 = next(
        (c for c in cons if isinstance(c, dict) and str(c.get("name", c.get("id"))) == session.cr_cprov_sel),
        None,
    )
    with detail_panel:
        if isinstance(pick0, dict):
            _render_constraint_detail(pick0, session.cr_cprov_sel)
