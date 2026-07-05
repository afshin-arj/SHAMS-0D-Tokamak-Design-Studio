"""Scan Lab cartography controls and run (Batch 4)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.scan_helpers import (
    SCAN_VAR_KEYS,
    SCAN_VAR_LABELS,
    build_scan_artifact_if_available,
    default_scan_bounds,
    run_cartography_scan,
)
from ui_nicegui.session import DesignSession


def _toggle_intent(session: DesignSession, intent: str, enabled: bool) -> None:
    cur = list(session.scan_cart_intents or [])
    if enabled and intent not in cur:
        cur.append(intent)
    elif not enabled and intent in cur:
        cur.remove(intent)
    session.scan_cart_intents = cur or ["Reactor"]


def render_cartography_controls(
    session: DesignSession,
    *,
    on_scan_complete: Optional[Callable[[], None]] = None,
) -> None:
    base = session.build_point_inputs()
    x_lo_def, x_hi_def, y_lo_def, y_hi_def = default_scan_bounds(
        base, session.scan_cart_x_key, session.scan_cart_y_key
    )

    ui.label("Cartography").classes("text-subtitle1")
    ui.label(
        "Map feasibility, dominance, and failure mechanisms across a 2D parameter slice."
    ).classes("text-caption text-grey q-mb-sm")

    _render_golden_presets(session, base, x_lo_def, x_hi_def, y_lo_def, y_hi_def)

    with ui.row().classes("w-full gap-4"):
        ui.select(
            SCAN_VAR_KEYS,
            label="x-axis",
            value=session.scan_cart_x_key,
            on_change=lambda e: setattr(session, "scan_cart_x_key", str(e.value)),
        ).props("dense").classes("flex-1")
        ui.select(
            SCAN_VAR_KEYS,
            label="y-axis",
            value=session.scan_cart_y_key,
            on_change=lambda e: setattr(session, "scan_cart_y_key", str(e.value)),
        ).props("dense").classes("flex-1")

    with ui.row().classes("w-full gap-4 items-center"):
        ui.label("Intent lenses:").classes("text-caption")
        for intent in ("Research", "Reactor"):
            ui.checkbox(
                intent,
                value=intent in (session.scan_cart_intents or []),
                on_change=lambda e, it=intent: _toggle_intent(session, it, bool(e.value)),
            )

    x_lo = session.scan_cart_x_lo if session.scan_cart_x_lo is not None else x_lo_def
    x_hi = session.scan_cart_x_hi if session.scan_cart_x_hi is not None else x_hi_def
    y_lo = session.scan_cart_y_lo if session.scan_cart_y_lo is not None else y_lo_def
    y_hi = session.scan_cart_y_hi if session.scan_cart_y_hi is not None else y_hi_def

    with ui.row().classes("w-full gap-2"):
        ui.number("x min", value=x_lo, step=0.1, on_change=lambda e: setattr(session, "scan_cart_x_lo", float(e.value))).classes("flex-1")
        ui.number("x max", value=x_hi, step=0.1, on_change=lambda e: setattr(session, "scan_cart_x_hi", float(e.value))).classes("flex-1")
        ui.number("y min", value=y_lo, step=0.1, on_change=lambda e: setattr(session, "scan_cart_y_lo", float(e.value))).classes("flex-1")
        ui.number("y max", value=y_hi, step=0.1, on_change=lambda e: setattr(session, "scan_cart_y_hi", float(e.value))).classes("flex-1")

    with ui.row().classes("w-full gap-4 items-center"):
        ui.slider(min=11, max=61, step=2, value=session.scan_cart_nx, on_change=lambda e: setattr(session, "scan_cart_nx", int(e.value))).props("label").classes("flex-1")
        ui.label(f"Nx={session.scan_cart_nx}").classes("text-caption")
        ui.slider(min=11, max=61, step=2, value=session.scan_cart_ny, on_change=lambda e: setattr(session, "scan_cart_ny", int(e.value))).props("label").classes("flex-1")
        ui.label(f"Ny={session.scan_cart_ny}").classes("text-caption")
        ui.checkbox(
            "Include compact outputs",
            value=session.scan_cart_include_outputs,
            on_change=lambda e: setattr(session, "scan_cart_include_outputs", bool(e.value)),
        )

    ui.label(
        f"Projection: {SCAN_VAR_LABELS.get(session.scan_cart_x_key, session.scan_cart_x_key)} "
        f"vs {SCAN_VAR_LABELS.get(session.scan_cart_y_key, session.scan_cart_y_key)}"
    ).classes("text-caption text-grey")

    if session.scan_running:
        ui.linear_progress(value=session.scan_progress, show_value=True).classes("w-full")
        if session.scan_progress_text:
            ui.label(session.scan_progress_text).classes("text-caption")

    async def _run_scan() -> None:
        if session.scan_running:
            ui.notify("Scan already running", type="warning")
            return
        xl = session.scan_cart_x_lo if session.scan_cart_x_lo is not None else x_lo_def
        xh = session.scan_cart_x_hi if session.scan_cart_x_hi is not None else x_hi_def
        yl = session.scan_cart_y_lo if session.scan_cart_y_lo is not None else y_lo_def
        yh = session.scan_cart_y_hi if session.scan_cart_y_hi is not None else y_hi_def
        if float(xh) <= float(xl) or float(yh) <= float(yl):
            ui.notify("Invalid bounds: max must exceed min on both axes", type="negative")
            return

        session.scan_running = True
        session.scan_progress = 0.0
        session.scan_progress_text = "Starting cartography scan…"
        ui.notify("Cartography scan started", type="info")

        def _progress(done: int, total: int) -> None:
            session.scan_progress = float(done) / max(float(total), 1.0)
            session.scan_progress_text = f"{done}/{total} points"

        try:
            rep = await run.io_bound(
                run_cartography_scan,
                session.build_point_inputs(),
                x_key=session.scan_cart_x_key,
                y_key=session.scan_cart_y_key,
                x_lo=float(xl),
                x_hi=float(xh),
                y_lo=float(yl),
                y_hi=float(yh),
                nx=int(session.scan_cart_nx),
                ny=int(session.scan_cart_ny),
                intents=list(session.scan_cart_intents or ["Reactor"]),
                include_outputs=bool(session.scan_cart_include_outputs),
                base_override=session.scan_cart_base_override,
                progress_cb=_progress,
            )
            session.scan_cartography_report = rep
            settings = {
                "x_key": session.scan_cart_x_key,
                "y_key": session.scan_cart_y_key,
                "x_lo": float(xl),
                "x_hi": float(xh),
                "y_lo": float(yl),
                "y_hi": float(yh),
                "nx": int(session.scan_cart_nx),
                "ny": int(session.scan_cart_ny),
                "intents": list(session.scan_cart_intents or ["Reactor"]),
                "include_outputs": bool(session.scan_cart_include_outputs),
            }
            artifact = build_scan_artifact_if_available(rep, settings)
            if isinstance(artifact, dict):
                session.scan_cartography_artifact = artifact
            ui.notify(f"Scan complete: {rep.get('n_points')} points", type="positive")
            if on_scan_complete:
                on_scan_complete()
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Scan failed: {exc}", type="negative")
        finally:
            session.scan_running = False
            session.scan_progress = 0.0
            session.scan_progress_text = ""

    btn = ui.button("Run cartography scan", icon="play_arrow", on_click=_run_scan).props("color=primary")
    if session.scan_running:
        btn.props("disable")


def _render_golden_presets(session, base, x_lo_def, x_hi_def, y_lo_def, y_hi_def) -> None:
    try:
        from tools.golden_scans import build_golden_scan_presets
    except ImportError:
        return

    presets = []
    try:
        presets = build_golden_scan_presets(base_inputs=base)
    except Exception:
        return
    if not presets:
        return

    labels = [str(p.get("label") or p.get("id") or "preset") for p in presets]
    with ui.expansion("Golden scans (teaching + QA)", icon="star").classes("w-full q-mb-sm"):
        pick = ui.select(labels, label="Preset", value=labels[0]).classes("w-full")

        def _load_golden() -> None:
            idx = labels.index(pick.value) if pick.value in labels else 0
            gp = presets[idx]
            session.scan_cart_x_key = str(gp.get("x_key") or session.scan_cart_x_key)
            session.scan_cart_y_key = str(gp.get("y_key") or session.scan_cart_y_key)
            session.scan_cart_intents = list(gp.get("intents") or ["Reactor"])
            xr = gp.get("x_range") or []
            yr = gp.get("y_range") or []
            if len(xr) >= 2:
                session.scan_cart_x_lo = float(xr[0])
                session.scan_cart_x_hi = float(xr[1])
            if len(yr) >= 2:
                session.scan_cart_y_lo = float(yr[0])
                session.scan_cart_y_hi = float(yr[1])
            session.scan_cart_nx = int(gp.get("n_x") or session.scan_cart_nx)
            session.scan_cart_ny = int(gp.get("n_y") or session.scan_cart_ny)
            bi = gp.get("base_inputs")
            if bi is not None:
                try:
                    from dataclasses import asdict
                    session.scan_cart_base_override = asdict(bi)
                except Exception:
                    session.scan_cart_base_override = None
            ui.notify("Loaded golden scan settings", type="positive")

        ui.button("Load golden scan", icon="upload", on_click=_load_golden).props("outline flat")
