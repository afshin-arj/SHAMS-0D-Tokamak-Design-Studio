"""Legacy nested Ti/H98/a/Q/g_conf scan — expert archive (solver-assisted)."""

from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.session import DesignSession

_LEGACY_CONTRACT = (
    "**Legacy nested grid** sweeps Ti, H98, minor radius, Q target, and g_conf. "
    "Each cell runs a **nested (Ip, fG) solver** — not frozen evaluate-only cartography. "
    "Use **cartography** for L0 slice truth; use this only for historical screening workflows."
)


def render_legacy_nested_panel(session: DesignSession) -> None:
    with ui.expansion("Legacy nested grid scan (expert)", icon="archive").classes("w-full"):
        ui.markdown(_LEGACY_CONTRACT).classes("text-caption q-mb-sm")

        try:
            from tools.legacy_nested_scan import (
                default_legacy_spec_from_session,
                estimate_legacy_grid_count,
                run_legacy_nested_scan,
            )
        except ImportError:
            ui.label("Legacy scan engine unavailable.").classes("text-negative")
            return

        spec = dict(getattr(session, "scan_legacy_spec", None) or default_legacy_spec_from_session(session))
        session.scan_legacy_spec = spec

        with ui.row().classes("gap-2 flex-wrap"):
            ui.number("Ti start [keV]", value=spec["Ti_start"], step=0.5, on_change=lambda e: spec.__setitem__("Ti_start", float(e.value))).classes("w-28")
            ui.number("Ti stop", value=spec["Ti_stop"], step=0.5, on_change=lambda e: spec.__setitem__("Ti_stop", float(e.value))).classes("w-28")
            ui.number("H98 start", value=spec["H98_start"], step=0.05, on_change=lambda e: spec.__setitem__("H98_start", float(e.value))).classes("w-28")
            ui.number("H98 stop", value=spec["H98_stop"], step=0.05, on_change=lambda e: spec.__setitem__("H98_stop", float(e.value))).classes("w-28")
            ui.number("Q start", value=spec["Q_start"], step=0.5, on_change=lambda e: spec.__setitem__("Q_start", float(e.value))).classes("w-24")
            ui.number("Q stop", value=spec["Q_stop"], step=0.5, on_change=lambda e: spec.__setitem__("Q_stop", float(e.value))).classes("w-24")

        n = estimate_legacy_grid_count(spec)
        ui.label(f"Solver grid evaluations (upper bound): {n}").classes("text-caption text-orange q-mb-sm")
        if n > 500:
            ui.label("Grid is large — tighten steps before running.").classes("text-caption text-negative")

        async def _run() -> None:
            if getattr(session, "scan_legacy_running", False):
                ui.notify("Legacy scan running", type="warning")
                return
            if n > 2000:
                ui.notify("Grid too large (>2000) — tighten bounds/steps.", type="negative")
                return
            session.scan_legacy_running = True
            ui.notify("Running legacy nested scan…", type="info")

            def _progress(done: int, total: int) -> None:
                session.scan_legacy_progress = float(done) / max(float(total), 1.0)

            try:
                rows, meta = await run.io_bound(
                    run_legacy_nested_scan,
                    dict(spec),
                    base_inputs=session.build_point_inputs(),
                    progress_cb=_progress,
                )
                session.scan_legacy_last = {"rows": rows, "meta": meta}
                ui.notify(f"Legacy scan: {len(rows)} feasible / {meta.get('n_total')} tried", type="positive")
                _results.refresh()
            except Exception as exc:
                ui.notify(f"Legacy scan failed: {exc}", type="negative")
            finally:
                session.scan_legacy_running = False
                session.scan_legacy_progress = 0.0

        ui.button("Run legacy nested scan", icon="grid_on", on_click=_run).props("outline q-mb-sm")
        _results(session)


@ui.refreshable
def _results(session: DesignSession) -> None:
    rep = getattr(session, "scan_legacy_last", None)
    if not isinstance(rep, dict):
        return
    meta = rep.get("meta") or {}
    rows = rep.get("rows") or []
    ui.label(
        f"Feasible: {meta.get('n_feasible', len(rows))} | "
        f"best g_conf: {meta.get('best_g_conf_found', '—')} | "
        f"{meta.get('run_seconds', 0):.1f} s"
    ).classes("text-caption")
    if rows:
        ui.button(
            "Download feasible rows JSON",
            icon="download",
            on_click=lambda: ui.download(
                json.dumps({"meta": meta, "rows": rows[:500]}, indent=2, default=str).encode(),
                "shams_legacy_nested_scan.json",
            ),
        ).props("flat outline")
