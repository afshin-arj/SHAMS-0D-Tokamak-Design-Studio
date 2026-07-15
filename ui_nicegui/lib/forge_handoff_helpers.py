"""Reactor Design Forge cross-deck handoffs."""
from __future__ import annotations

from typing import Any, Dict

from ui_nicegui.lib.compare_helpers import send_row_to_compare_slot
from ui_nicegui.lib.pareto_interpret_helpers import scan_lab_focus, systems_mode_handoff


def archive_row_handoff_payload(run: dict, row_idx: int) -> Dict[str, Any]:
    archive = run.get("archive") or []
    if row_idx < 0 or row_idx >= len(archive):
        raise IndexError("Invalid archive row")
    row = archive[row_idx]
    if not isinstance(row, dict):
        raise ValueError("Invalid archive entry")
    payload = dict(row.get("inputs") or {})
    outs = row.get("outputs") or {}
    if isinstance(outs, dict):
        payload.update(outs)
    payload["failure_mode"] = row.get("failure_mode")
    payload["min_signed_margin"] = row.get("min_signed_margin")
    payload["feasible"] = row.get("feasible")
    return payload


def send_archive_row_to_compare(session, run: dict, row_idx: int, slot: str) -> None:
    payload = archive_row_handoff_payload(run, row_idx)
    send_row_to_compare_slot(session, payload, slot, label="Reactor Design Forge")


def handoff_archive_row_to_scan_lab(session, run: dict, row_idx: int) -> dict:
    payload = archive_row_handoff_payload(run, row_idx)
    bounds = dict(session.forge_mf_last_bounds or {})
    if not bounds:
        bounds = {k: [payload.get(k), payload.get(k)] for k in payload if k.endswith("_m") or k.endswith("_MA")}
    objectives = {}
    lens = session.forge_lens_contract if isinstance(session.forge_lens_contract, dict) else {}
    for o in lens.get("objectives") or []:
        if isinstance(o, dict) and o.get("key"):
            objectives[str(o["key"])] = str(o.get("sense") or "min")
    focus = scan_lab_focus(payload, bounds, objectives)
    focus["source"] = "Reactor Design Forge"
    session.scan_probe_focus = focus
    if focus.get("x_key"):
        session.scan_cart_x_key = str(focus["x_key"])
    if focus.get("y_key"):
        session.scan_cart_y_key = str(focus["y_key"])
    session.scan_workflow_step = "1 · Setup & Run"
    return focus


def handoff_archive_row_to_systems_mode(session, run: dict, row_idx: int) -> dict:
    payload = archive_row_handoff_payload(run, row_idx)
    bounds = dict(session.forge_mf_last_bounds or {})
    cand = systems_mode_handoff(payload, bounds)
    session.systems_mode_queue = [cand]
    session.systems_workflow_step = "1 · Targets"
    return cand
