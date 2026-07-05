"""Ledgers telemetry view — power + authority budgets."""
from __future__ import annotations

import json

from nicegui import ui

from ui_nicegui.lib.pd_parity_helpers import fmt_num, pin_ploss_closure_mw, power_ledger_badged_rows
from ui_nicegui.session import DesignSession


def render_ledgers(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not isinstance(out, dict):
        return

    include_rad = bool(session.overlay.get("include_radiation", False))

    ui.label("Power Ledger — Closure Table").classes("text-subtitle1")
    ui.label("Transparent Pin/Pout bookkeeping at this point (0-D proxies).").classes("text-caption")
    rows = power_ledger_badged_rows(out, include_radiation=include_rad)
    if rows:
        ui.table(
            columns=[
                {"name": "item", "label": "Item", "field": "item", "align": "left"},
                {"name": "key", "label": "Key", "field": "key", "align": "left"},
                {"name": "MW", "label": "MW", "field": "MW"},
                {"name": "type", "label": "Type", "field": "type"},
            ],
            rows=rows,
            row_key="key",
        ).classes("w-full")
        closure = pin_ploss_closure_mw(out)
        if closure is not None:
            ui.label(f"Closure check: Pin − Ploss = {closure:.4g} MW").classes("text-body2 q-mt-sm")
    else:
        ui.label("No power ledger channels in outputs.").classes("text-caption")

    ui.separator()
    ui.label("Control budget ledger").classes("text-subtitle1")
    budg = out.get("control_budget_ledger")
    if isinstance(budg, dict) and budg:
        brows = [{"key": str(k), "value": fmt_num(v)} for k, v in budg.items()]
        ui.table(
            columns=[
                {"name": "key", "label": "Key", "field": "key", "align": "left"},
                {"name": "value", "label": "Value", "field": "value", "align": "left"},
            ],
            rows=brows,
            row_key="key",
        ).classes("w-full")
    else:
        ui.label("No control budget ledger (enable control contracts in Configure).").classes("text-caption")

    auth = out.get("control_contracts_authority")
    if isinstance(auth, dict) and auth:
        ui.separator()
        ui.label("Control contracts authority tags").classes("text-subtitle2")
        ui.code(json.dumps(auth, indent=2, sort_keys=True, default=str)).classes("w-full")

    v402 = out.get("dominance_order_v402")
    if isinstance(v402, list) and v402 and bool(out.get("include_authority_dominance_v402")):
        ui.separator()
        ui.label("Dominance ranking").classes("text-subtitle2")
        if v402 and isinstance(v402[0], dict):
            cols = [{"name": c, "label": c, "field": c, "align": "left"} for c in v402[0].keys()]
            ui.table(columns=cols, rows=v402[:20], row_key=cols[0]["field"]).classes("w-full")
