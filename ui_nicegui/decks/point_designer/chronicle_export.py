"""Chronicle & Export telemetry view."""
from __future__ import annotations

import json
from pathlib import Path

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.decks.point_designer.export_ui import render_export
from ui_nicegui.lib.pd_parity_helpers import radial_build_png_bytes
from ui_nicegui.lib.pd_solver_helpers import search_nearest_feasible
from ui_nicegui.session import DesignSession


def _trace_table(trace: list) -> None:
    if not trace:
        ui.label("No solver trace recorded for this run.").classes("text-caption")
        return
    iter_rows = [r for r in trace if r.get("iter") is not None or r.get("event") == "iter"]
    if not iter_rows:
        ui.code(json.dumps(trace, indent=2, default=str)).classes("w-full")
        return
    cols = [
        {"name": "iter", "label": "iter", "field": "iter", "align": "left"},
        {"name": "Ip_MA", "label": "Ip (MA)", "field": "Ip_MA", "align": "left"},
        {"name": "fG", "label": "fG", "field": "fG", "align": "left"},
        {"name": "H98", "label": "H98", "field": "H98", "align": "left"},
        {"name": "Q", "label": "Q", "field": "Q", "align": "left"},
        {"name": "residual", "label": "residual", "field": "residual", "align": "left"},
    ]
    ui.table(columns=cols, rows=iter_rows[:80], row_key="iter").classes("w-full")


def render_chronicle_export(session: DesignSession) -> None:
    ui.label("Chronicle & Export").classes("text-subtitle1")

    log_lines = list(session.pd_last_log_lines or [])
    solver_log = "\n".join(log_lines).strip() + ("\n" if log_lines else "")

    with ui.expansion("Solver log (this run)", icon="history").classes("w-full"):
        if solver_log.strip():
            ui.download(
                solver_log.encode("utf-8"),
                "point_designer_solver.log",
                "Download solver log",
            ).classes("q-mb-sm")
        ui.textarea(value=solver_log or "(empty — direct evaluate or no run yet)").props(
            "readonly outlined dense"
        ).classes("w-full").style("font-family: monospace; font-size: 11px;")

    if session.pd_show_solver_live and session.pd_solver_trace:
        with ui.expansion("Live convergence trace", icon="show_chart").classes("w-full"):
            _trace_table(session.pd_solver_trace)

    log_path = Path(repo_root()) / "runs" / "activity_log_current.log"
    tail = ""
    try:
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = "\n".join(lines[-80:])
    except Exception:
        tail = ""

    with ui.expansion("Activity chronicle (tail)", icon="article").classes("w-full"):
        ui.textarea(value=tail or "(empty)").props("readonly outlined dense").classes("w-full").style(
            "font-family: monospace; font-size: 11px;"
        )

    if session.pd_eval_mode in ("solver", "envelope"):
        with ui.expansion("Nearest feasible search (frontier)", icon="search").classes("w-full"):
            ui.label(
                "If the solver cannot hit (H98, Q) inside bounds, search for the nearest feasible point."
            ).classes("text-caption q-mb-sm")

            async def _search() -> None:
                ui.notify("Searching nearest feasible…", type="info")
                try:
                    rep = await run.io_bound(search_nearest_feasible, session)
                    if rep.get("status") == "error":
                        ui.notify(str(rep.get("message", "frontier error")), type="negative")
                    else:
                        ui.notify("Frontier search complete.", type="positive")
                    _frontier_panel.refresh()
                except Exception as exc:
                    ui.notify(f"Frontier search failed: {exc}", type="negative")

            ui.button("Search nearest feasible within bounds", on_click=_search).classes("q-mb-sm")
            _frontier_panel(session)

    art = session.pd_last_artifact
    if isinstance(art, dict) and art.get("run_summary"):
        with ui.expansion("Run summary (copy/paste)", icon="summarize").classes("w-full"):
            rs = art["run_summary"]
            lines = []
            if isinstance(rs, dict):
                for k, v in rs.items():
                    if k != "tightest_hard_constraints":
                        lines.append(f"{k}: {v}")
            ui.code("\n".join(lines) or json.dumps(rs, indent=2, default=str)).classes("w-full")

    with ui.expansion("Export bay — artifacts & downloads", icon="download").classes("w-full"):
        render_compare_slot_actions(session)
        render_radial_build_export(session)
        render_export(session)


def render_compare_slot_actions(session: DesignSession) -> None:
    """Send current run artifact to Compare deck slots A/B."""
    import time

    art = session.pd_last_artifact
    if not isinstance(art, dict):
        return

    ui.label("Quick interop: send the current run to Compare without downloading files.").classes("text-caption")
    with ui.row().classes("gap-2 q-mb-sm"):
        def _send_a() -> None:
            session.cmp_slot_a = dict(art)
            session.cmp_slot_a_meta = {
                "ts_unix": float(time.time()),
                "inputs_hash": str(session.pd_last_inputs_hash or session.pd_current_inputs_hash or ""),
                "label": "Point Designer (last run)",
            }
            ui.notify("Sent current run to Compare Slot A.", type="positive")

        def _send_b() -> None:
            session.cmp_slot_b = dict(art)
            session.cmp_slot_b_meta = {
                "ts_unix": float(time.time()),
                "inputs_hash": str(session.pd_last_inputs_hash or session.pd_current_inputs_hash or ""),
                "label": "Point Designer (last run)",
            }
            ui.notify("Sent current run to Compare Slot B.", type="positive")

        def _clear() -> None:
            session.cmp_slot_a = None
            session.cmp_slot_b = None
            session.cmp_slot_a_meta = {}
            session.cmp_slot_b_meta = {}
            ui.notify("Cleared Compare slots.", type="info")

        ui.button("Send to Compare Slot A", on_click=_send_a).props("outline")
        ui.button("Send to Compare Slot B", on_click=_send_b).props("outline")
        ui.button("Clear Compare Slots", on_click=_clear).props("flat")


def render_radial_build_export(session: DesignSession) -> None:
    art = session.pd_last_artifact
    if not isinstance(art, dict):
        return
    png = session.pd_last_radial_png_bytes
    if not png:
        png = radial_build_png_bytes(art)
        if png:
            session.pd_last_radial_png_bytes = png
    if png:
        ui.download(png, "shams_radial_build.png", "Download radial build PNG").classes("q-mt-sm")
    else:
        ui.label("Radial-build export unavailable for this point.").classes("text-caption q-mt-sm")


@ui.refreshable
def _frontier_panel(session: DesignSession) -> None:
    rep = session.pd_frontier_last
    if not isinstance(rep, dict) or not rep:
        return
    if rep.get("status") == "error":
        ui.label(str(rep.get("message", "frontier error"))).classes("text-negative")
        return
    best = rep.get("best_levers") or {}
    ui.label(
        f"Best Ip={best.get('Ip_MA', float('nan')):.4g} MA, fG={best.get('fG', float('nan')):.4g} | "
        f"score={rep.get('best_score', float('nan')):.4g}"
    ).classes("text-body2")
