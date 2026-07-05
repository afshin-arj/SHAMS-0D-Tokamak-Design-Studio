"""Promote candidate to Point Designer."""

from __future__ import annotations

import time

from nicegui import run, ui

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.pd_artifact_helpers import build_point_artifact
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.lib.systems_workflow_helpers import apply_x_to_session, collect_candidates
from ui_nicegui.session import DesignSession


def render_apply_panel(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Promote candidate to Point Designer").classes("text-subtitle1")
    ui.label(
        "Applies iteration variables to PD inputs, then re-evaluates through the frozen Evaluator choke point."
    ).classes("text-caption q-mb-sm")

    cands = collect_candidates(session)
    if not cands:
        ui.label("No candidates — run recovery or search on **3 · Alternatives**.").classes("text-grey")
        return

    labels = [
        f"{c['source']} | Q={((c.get('headline') or {}).get('Q', '-'))} | feasible={c.get('feasible')}"
        for c in cands
    ]
    if session.systems_selected_candidate_id not in [c["id"] for c in cands]:
        session.systems_selected_candidate_id = cands[0]["id"]

    ui.select(
        labels,
        label="Candidate",
        value=labels[[c["id"] for c in cands].index(session.systems_selected_candidate_id)],
        on_change=lambda e: _pick(session, cands, labels, str(e.value)),
    ).classes("w-full q-mb-sm")

    sel = _selected(cands, session.systems_selected_candidate_id)
    if sel and isinstance(sel.get("x"), dict) and session.systems_expert_view:
        with ui.expansion("Candidate variables (expert)"):
            ui.json(sel["x"])

    async def _apply_evaluate() -> None:
        sel_now = _selected(cands, session.systems_selected_candidate_id)
        if not sel_now or not isinstance(sel_now.get("x"), dict):
            ui.notify("No candidate selected", type="warning")
            return
        applied = apply_x_to_session(session, sel_now["x"])
        ui.notify(f"Applied {len(applied)} variables", type="info")
        try:
            inp = session.build_point_inputs()
            out = await run.io_bound(
                ui_evaluate,
                inp,
                origin="NiceGUI:SystemsApply",
                Paux_for_Q_MW=session.paux_for_q,
            )
            inputs_dict = inp.to_dict() if hasattr(inp, "to_dict") else dict(session.inputs)
            set_point_evaluation(session, outputs=out, inputs=inputs_dict)
            session.systems_last_solve_artifact = build_point_artifact(
                inputs=inputs_dict,
                outputs=out,
                design_intent=session.design_intent,
            )
            ui.notify("Re-evaluated via Point Designer", type="positive")
            if on_complete:
                on_complete()
        except Exception as exc:
            ui.notify(f"Apply failed: {exc}", type="negative")

    async def _send_compare(slot: str) -> None:
        sel_now = _selected(cands, session.systems_selected_candidate_id)
        if not sel_now or not isinstance(sel_now.get("x"), dict):
            return
        apply_x_to_session(session, sel_now["x"])
        inp = session.build_point_inputs()
        out = await run.io_bound(
            ui_evaluate,
            inp,
            origin="NiceGUI:SystemsCompare",
            Paux_for_Q_MW=session.paux_for_q,
        )
        inputs_dict = inp.to_dict() if hasattr(inp, "to_dict") else dict(session.inputs)
        art = build_point_artifact(inputs=inputs_dict, outputs=out, design_intent=session.design_intent)
        meta = {"ts_unix": time.time(), "label": f"Systems ({sel_now.get('source')})"}
        if slot == "A":
            session.cmp_slot_a = art
            session.cmp_slot_a_meta = meta
        else:
            session.cmp_slot_b = art
            session.cmp_slot_b_meta = meta
        ui.notify(f"Sent to Compare slot {slot}", type="positive")

    ui.button("Apply to PD & re-evaluate", icon="check", on_click=_apply_evaluate).props("color=primary w-full q-mb-sm")
    with ui.row().classes("gap-2"):
        ui.button("Compare slot A", on_click=lambda: _send_compare("A")).props("outline")
        ui.button("Compare slot B", on_click=lambda: _send_compare("B")).props("outline")


def _pick(session: DesignSession, cands: list, labels: list, label: str) -> None:
    try:
        session.systems_selected_candidate_id = cands[labels.index(label)]["id"]
    except ValueError:
        pass


def _selected(cands: list, cid: str) -> dict | None:
    for c in cands:
        if c.get("id") == cid:
            return c
    return cands[0] if cands else None
