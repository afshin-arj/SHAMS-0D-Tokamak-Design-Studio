"""Scan Lab post-run results panel."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.scan_helpers import dominance_table_rows, report_to_json_bytes, summarize_scan_report
from ui_nicegui.lib.scan_v396_display import extract_v396_transport, format_v396_caption


def render_scan_results(session, rep: dict) -> None:
    summary = summarize_scan_report(rep)
    if not summary.get("loaded"):
        return

    # Optional v396 strip from baseline point outputs and/or sample scan cells.
    v396_src = None
    point_out = getattr(session, "pd_last_outputs", None)
    if isinstance(point_out, dict):
        v396_src = extract_v396_transport(point_out)
    if v396_src is None:
        pts = rep.get("points") or []
        for p in pts[:40]:
            if not isinstance(p, dict):
                continue
            outs = p.get("outputs")
            v396_src = extract_v396_transport(outs if isinstance(outs, dict) else None)
            if v396_src:
                break
    if v396_src:
        cap = format_v396_caption(v396_src)
        if cap:
            ui.markdown(
                f"**v396 transport envelope (PROXY):** {cap} — multi-scaling screening, not a transport solver."
            ).classes("text-caption text-grey q-mb-xs")

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
