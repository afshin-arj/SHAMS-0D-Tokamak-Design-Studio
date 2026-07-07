"""Feasibility forensics panel — NiceGUI Phase 11."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.pd_forensics_helpers import run_local_forensics
from ui_nicegui.lib.pd_parity_helpers import lever_recipe_tables
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_forensics(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Feasibility Forensics — Local Sensitivity").classes("text-subtitle1")
    ui.label(
        "Deterministic finite-difference sensitivities of constraint signed margins. "
        "Diagnostic only — no optimization, no truth mutation."
    ).classes("text-caption q-mb-sm")

    async def _compute() -> None:
        ui.notify("Computing forensics…", type="info")
        try:
            base = session.build_point_inputs()
            ff = await run.io_bound(
                run_local_forensics,
                base,
                design_intent=session.design_intent,
            )
            session.pd_last_forensics = ff
            _attach_forensics_to_artifact(session, ff)
            ui.notify("Forensics complete.", type="positive")
            _panel.refresh()
            if on_complete:
                on_complete()
        except Exception as exc:
            session.pd_last_forensics = {"status": "error", "message": str(exc)}
            ui.notify(f"Forensics failed: {exc}", type="negative")
            _panel.refresh()

    ui.button("Compute forensics", icon="analytics", on_click=_compute).props("outline q-mb-sm")
    _panel(session)


def _attach_forensics_to_artifact(session: DesignSession, ff: dict) -> None:
    art = session.pd_last_artifact
    if isinstance(art, dict) and isinstance(ff, dict) and ff.get("status") != "error":
        art.setdefault("studies", {})
        art["studies"]["feasibility_forensics"] = ff


@ui.refreshable
def _panel(session: DesignSession) -> None:
    ff = session.pd_last_forensics
    if not isinstance(ff, dict) or not ff:
        ui.label("Click **Compute forensics** after evaluating a point.").classes("text-caption text-grey")
        return

    if ff.get("status") == "error":
        ui.label(str(ff.get("message", "forensics error"))).classes("text-negative")
        return

    b = ff.get("base") or {}
    dom = str(b.get("top_dominant", ""))
    frag = b.get("fragility_fraction", float("nan"))
    stab = str(b.get("stability_label", "unknown"))
    lc = ff.get("lever_confidence") or {}
    lc_label = str(lc.get("label", "unknown"))

    frag_s = f"{float(frag):.2f}" if isinstance(frag, (int, float)) and frag == frag else "n/a"
    kpi_row([
        ("Dominant blocker", dom or "(none)"),
        ("Stability", stab),
        ("Fragility", frag_s),
        ("Lever confidence", lc_label),
    ])

    notes = ff.get("notes") or []
    if notes:
        ui.label("Why this point is (un)stable").classes("text-subtitle2 q-mt-sm")
        for n in notes[:6]:
            ui.label(f"• {n}").classes("text-body2")

    tornado = ff.get("tornado") or {}
    focus = ff.get("focus_constraints") or []
    if tornado and focus:
        pick = ui.select(list(focus), label="Constraint to inspect", value=focus[0])
        _tornado_table(tornado, pick)

    help_rows, hurt_rows, dom_c = lever_recipe_tables(ff)
    if dom_c:
        ui.label(f"Lever recipe (local-linear) — dominant blocker: {dom_c}").classes("text-subtitle2 q-mt-md")
        ui.label(
            "Directional suggestions from local linearization at the probe step Δx. "
            "Not an optimizer; may not hold far from this point."
        ).classes("text-caption")
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                ui.label("Increase-margin levers").classes("text-subtitle2")
                if help_rows:
                    ui.table(
                        columns=[
                            {"name": "knob", "label": "Knob", "field": "knob", "align": "left"},
                            {"name": "action", "label": "Direction", "field": "action"},
                            {"name": "Δx", "label": "Δx", "field": "Δx"},
                            {"name": "Δmargin @ Δx", "label": "Δmargin", "field": "Δmargin @ Δx"},
                            {"name": "|Δmargin|", "label": "|Δmargin|", "field": "|Δmargin|"},
                        ],
                        rows=help_rows,
                        row_key="knob",
                    ).classes("w-full")
                else:
                    ui.label("No positive-slope levers at current probe set.").classes("text-caption")
            with ui.column().classes("flex-1"):
                ui.label("Avoid / regression levers").classes("text-subtitle2")
                ui.label("Knobs that decrease margin when increased; decreasing them helps.").classes("text-caption")
                if hurt_rows:
                    ui.table(
                        columns=[
                            {"name": "knob", "label": "Knob", "field": "knob", "align": "left"},
                            {"name": "action", "label": "Direction", "field": "action"},
                            {"name": "Δx", "label": "Δx", "field": "Δx"},
                            {"name": "Δmargin @ Δx", "label": "Δmargin", "field": "Δmargin @ Δx"},
                            {"name": "|Δmargin|", "label": "|Δmargin|", "field": "|Δmargin|"},
                        ],
                        rows=hurt_rows,
                        row_key="knob",
                    ).classes("w-full")
                else:
                    ui.label("No negative-slope levers at current probe set.").classes("text-caption")

    with ui.expansion("Raw forensics JSON").classes("w-full q-mt-sm"):
        render_json_blob(ff)


def _tornado_table(tornado: dict, pick_select) -> None:
    @ui.refreshable
    def _table() -> None:
        pick = str(pick_select.value or "")
        rows = list(tornado.get(pick, []) or [])
        if not rows:
            ui.label("No sensitivity rows for this constraint.").classes("text-caption")
            return
        table_rows = []
        for r in rows:
            sgn = str(r.get("sign", "0"))
            effect = "margin ↑" if sgn == "+" else ("margin ↓" if sgn == "-" else "flat")
            table_rows.append({
                "knob": r.get("knob"),
                "dmargin_per_unit": r.get("dmargin_per_unit"),
                "step": r.get("step"),
                "impact_abs": r.get("impact_abs"),
                "effect": effect,
            })
        ui.table(
            columns=[
                {"name": "knob", "label": "Knob", "field": "knob", "align": "left"},
                {"name": "dmargin_per_unit", "label": "∂margin/∂x", "field": "dmargin_per_unit"},
                {"name": "step", "label": "Δx", "field": "step"},
                {"name": "impact_abs", "label": "|Δmargin| @ Δx", "field": "impact_abs"},
                {"name": "effect", "label": "Local lever", "field": "effect"},
            ],
            rows=table_rows,
            row_key="knob",
        ).classes("w-full")

    pick_select.on("update:model-value", lambda: _table.refresh())
    _table()
