"""Constraints tab — briefing, pipeline diff, NO-SOLUTION atlas, notebook."""
from __future__ import annotations

import math
from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.components.workflow_cta import render_goto_setup_button
from ui_nicegui.lib.pd_intent_policy import classify_failed_constraints, policy_caption
from ui_nicegui.lib.pd_parity_helpers import (
    constraint_notebook_rows,
    failed_hard_names,
    no_solution_atlas_summary,
    pipeline_diff_rows,
)
from ui_nicegui.lib.verdict_core import constraint_table_rows
from ui_nicegui.decks.point_designer.configure_systems_bridge import render_systems_precheck_bridge
from ui_nicegui.session import DesignSession


def _fmt(v) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
        if math.isnan(f):
            return "nan"
        return f"{f:.4g}"
    except (TypeError, ValueError):
        return str(v)


def render_constraints(
    session: DesignSession,
    *,
    on_refresh: Optional[Callable[[], None]] = None,
) -> None:
    out = session.pd_last_outputs or session.last_eval
    ui.label("Constraint Briefing").classes("text-h6")
    ui.label(f"Design intent: {session.design_intent}").classes("text-caption")
    ui.label(policy_caption(session.design_intent)).classes("text-caption text-grey q-mb-sm")
    if session.explain_mode:
        ui.label(
            "Explain mode: constraint notebook includes binding reasons where the evaluator exposes them."
        ).classes("text-caption text-blue-grey q-mb-sm")

    if not isinstance(out, dict) or not out:
        ui.label("Run **Evaluate Point** to see constraint checks.").classes("text-grey")
        render_goto_setup_button(
            session,
            attr="pd_workflow_tab",
            step="1 · Configure",
            label="Go to Configure",
            on_refresh=on_refresh,
        )
        return

    failed = failed_hard_names(out)
    cls = classify_failed_constraints(failed, design_intent=session.design_intent)
    if cls["blocking"] or cls["diagnostic"] or cls["ignored"]:
        with ui.card().classes("w-full q-mb-sm"):
            ui.label("Intent-aware constraint summary").classes("text-subtitle2")
            if cls["blocking"]:
                ui.markdown("**Blocking:** " + ", ".join(f"`{x}`" for x in cls["blocking"]))
            if cls["diagnostic"]:
                ui.markdown("**Diagnostics:** " + ", ".join(f"`{x}`" for x in cls["diagnostic"]))
                if any(x in cls["diagnostic"] for x in ("q_div", "P_SOL/R")):
                    ui.label(
                        "Divertor / exhaust listed as diagnostic under Research — "
                        "physics margin still names the kill; switch to Reactor hard-set for compliance claims."
                    ).classes("text-caption text-orange")
            if cls["ignored"]:
                ui.markdown("**Ignored:** " + ", ".join(f"`{x}`" for x in cls["ignored"]))

    with ui.expansion("Constraint pipeline diff (registry vs legacy)", icon="compare").classes("w-full"):
        _render_pipeline_diff(out, session.design_intent)

    with ui.expansion("NO-SOLUTION mechanism atlas", icon="map").classes("w-full"):
        _render_atlas(out, session.design_intent)

    with ui.expansion("Constraint ledger (sorted by residual)", icon="rule").classes("w-full"):
        rows_raw = constraint_table_rows(out)
        table_rows = [{
            "status": "PASS" if r.get("passed") else "FAIL",
            "name": str(r.get("name", "")),
            "value": _fmt(r.get("value")),
            "limit": _fmt(r.get("limit")),
            "sense": str(r.get("sense", "")),
            "residual": _fmt(r.get("residual")),
        } for r in rows_raw]
        ui.table(
            columns=[
                {"name": "status", "label": "Status", "field": "status"},
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "value", "label": "Value", "field": "value"},
                {"name": "limit", "label": "Limit", "field": "limit"},
                {"name": "sense", "label": "Sense", "field": "sense"},
                {"name": "residual", "label": "Residual", "field": "residual"},
            ],
            rows=table_rows,
            row_key="name",
        ).classes("w-full")

    with ui.expansion("Constraint notebook", icon="menu_book").classes("w-full"):
        for row in constraint_notebook_rows(out):
            title = f"{'PASS' if row['passed'] else 'FAIL'} — {row['name']}"
            with ui.expansion(title).classes("w-full"):
                ui.label(
                    f"value={_fmt(row['value'])} limit={_fmt(row['limit'])} "
                    f"sense={row['sense']} group={row['group']}"
                ).classes("text-caption")
                if row.get("note"):
                    ui.label(str(row["note"])).classes("text-caption text-grey")

    failed_rows = [r for r in table_rows if r["status"] == "FAIL"]
    if failed_rows:
        ui.label(f"{len(failed_rows)} hard constraint(s) failing.").classes("text-negative q-mt-sm")
    else:
        ui.label("All governance hard constraints pass.").classes("text-positive q-mt-sm")

    render_systems_precheck_bridge(session)


def _render_pipeline_diff(out: dict, design_intent: str) -> None:
    data = pipeline_diff_rows(out, design_intent=design_intent)
    aligned = data["aligned"]
    ui.label(f"Pipeline parity: {'aligned' if aligned else 'misaligned'}").classes(
        "text-weight-bold " + ("text-positive" if aligned else "text-negative")
    )
    parity = data["parity"]
    ui.label(
        f"Registry specs: {parity.get('registry_n_specs', 0)} | "
        f"Gov {parity.get('n_governance', 0)} / Ledger {parity.get('n_ledger', 0)} | "
        f"Mismatches: {parity.get('n_pass_mismatch', 0)}"
    ).classes("text-caption")
    with ui.row().classes("w-full gap-2"):
        for title, key in (
            ("Registry", "registry_governance"),
            ("Legacy", "legacy_governance"),
            ("Merged", "merged_governance"),
        ):
            with ui.column().classes("flex-1"):
                ui.label(title).classes("text-caption text-weight-bold")
                rows = data.get(key) or []
                if rows:
                    cols = [{"name": c, "label": c, "field": c, "align": "left"} for c in rows[0].keys()]
                    ui.table(columns=cols, rows=rows[:40], row_key=cols[0]["field"]).classes("w-full")


def _render_atlas(out: dict, design_intent: str) -> None:
    atlas = no_solution_atlas_summary(out, design_intent=design_intent)
    color = "text-positive" if atlas["verdict"] == "FEASIBLE" else "text-negative"
    ui.label(f"Atlas verdict: {atlas['verdict']}").classes(f"text-weight-bold {color}")
    ui.label(f"Dominant mechanism: {atlas['dominant_mechanism']}").classes("text-caption")
    ui.label(f"Dominant constraint: {atlas['dominant_constraint']}").classes("text-caption")
    if atlas["mechanism_rows"]:
        ui.table(
            columns=[
                {"name": "mechanism", "label": "Mechanism", "field": "mechanism", "align": "left"},
                {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
            ],
            rows=atlas["mechanism_rows"],
            row_key="constraint",
        ).classes("w-full")
