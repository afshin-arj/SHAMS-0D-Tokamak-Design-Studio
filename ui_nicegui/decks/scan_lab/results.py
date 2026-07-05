"""Scan Lab post-run results panel."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.scan_helpers import dominance_table_rows, report_to_json_bytes, summarize_scan_report


def render_scan_results(session, rep: dict) -> None:
    summary = summarize_scan_report(rep)
    if not summary.get("loaded"):
        return

    nar_all = rep.get("narrative") or {}
    nar_int = (nar_all.get("intents") or {}) if isinstance(nar_all, dict) else {}
    intents = rep.get("intents") or ["Reactor"]
    all_zero = True
    worst: dict[str, str] = {}
    for it in intents:
        nn = nar_int.get(str(it), {}) if isinstance(nar_int, dict) else {}
        ff = float(nn.get("blocking_feasible_rate", 0.0)) if isinstance(nn, dict) else 0.0
        if ff > 0.0:
            all_zero = False
        rk = (nn.get("dominance_ranked") or []) if isinstance(nn, dict) else []
        if rk and isinstance(rk[0], dict):
            worst[str(it)] = str(rk[0].get("constraint") or "")

    if all_zero:
        ui.label(
            "No blocking-feasible region exists in this X–Y space (under the selected assumptions)."
        ).classes("text-orange q-mt-sm")
        for k, v in worst.items():
            if v:
                ui.markdown(f"- Under **{k}** intent, **{v}** limits essentially everywhere.")

    rows = dominance_table_rows(rep)
    if rows:
        with ui.expansion("Dominance ranking", icon="leaderboard").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                    {"name": "fraction", "label": "Fraction", "field": "fraction"},
                    {"name": "count", "label": "Count", "field": "count"},
                ],
                rows=rows,
                row_key="constraint",
            ).classes("w-full")

    data = report_to_json_bytes(rep)
    ui.button(
        "Download scan report JSON",
        icon="download",
        on_click=lambda: ui.download(data, "shams_scan_cartography.json"),
    ).props("outline").classes("q-mt-sm")
