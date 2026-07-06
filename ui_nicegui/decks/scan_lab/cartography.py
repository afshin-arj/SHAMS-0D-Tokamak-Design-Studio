"""Scan Lab cartography controls and run."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.scan_helpers import (
    SCAN_VAR_KEYS,
    SCAN_VAR_LABELS,
    baseline_axis_values,
    build_scan_artifact_if_available,
    default_scan_bounds,
    estimate_eval_count,
    run_cartography_scan,
)
from ui_nicegui.lib.scan_labels import INTENT_HELP, PROJECTION_CAVEAT, RECOMMENDED_SLICES, ROBUSTNESS_GLOSSARY
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

    ui.label("Run cartography").classes("text-subtitle1")
    ui.label(
        "Map feasibility, dominant limiters, and failure mechanisms across a 2D parameter slice."
    ).classes("text-caption text-grey q-mb-sm")
    ui.markdown(INTENT_HELP).classes("text-caption q-mb-xs")
    ui.markdown(PROJECTION_CAVEAT).classes("text-caption text-orange q-mb-xs")
    if session.scan_teaching_mode:
        ui.markdown(ROBUSTNESS_GLOSSARY).classes("text-caption text-grey q-mb-sm")

    ax = baseline_axis_values(base, session.scan_cart_x_key, session.scan_cart_y_key)
    with ui.row().classes("gap-3 flex-wrap q-mb-sm"):
        with ui.card().classes("p-2"):
            ui.label("Baseline at slice axes").classes("text-caption text-grey")
            ui.label(
                f"{SCAN_VAR_LABELS.get(ax['x_key'], ax['x_key'])} = {ax['x_val']:.4g} · "
                f"{SCAN_VAR_LABELS.get(ax['y_key'], ax['y_key'])} = {ax['y_val']:.4g}"
            ).classes("text-body2")

    ui.label("Recommended slices").classes("text-caption text-grey")
    with ui.row().classes("gap-2 flex-wrap q-mb-sm"):
        for label, xk, yk in RECOMMENDED_SLICES:

            def _apply_slice(_xk=xk, _yk=yk) -> None:
                session.scan_cart_x_key = _xk
                session.scan_cart_y_key = _yk
                session.scan_cart_x_lo = None
                session.scan_cart_x_hi = None
                session.scan_cart_y_lo = None
                session.scan_cart_y_hi = None
                ui.notify(f"Slice: {label}", type="info")

            ui.button(label, on_click=_apply_slice).props("flat dense outline")

    if session.scan_cart_base_override:
        ui.badge("Golden-scan baseline override active", color="orange").props("outline q-mb-sm")

    axis_opts = {k: SCAN_VAR_LABELS.get(k, k) for k in SCAN_VAR_KEYS}
    with ui.row().classes("w-full gap-4"):
        ui.select(
            axis_opts,
            label="X axis",
            value=session.scan_cart_x_key,
            on_change=lambda e: setattr(session, "scan_cart_x_key", str(e.value)),
        ).props("dense").classes("flex-1")
        ui.select(
            axis_opts,
            label="Y axis",
            value=session.scan_cart_y_key,
            on_change=lambda e: setattr(session, "scan_cart_y_key", str(e.value)),
        ).props("dense").classes("flex-1")

    if session.scan_cart_x_key == session.scan_cart_y_key:
        ui.label("X and Y must differ — pick two independent parameters.").classes(
            "text-caption text-negative q-mb-sm"
        )

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
            "Include compact outputs (Q, H98, Pfus, contours)",
            value=session.scan_cart_include_outputs,
            on_change=lambda e: setattr(session, "scan_cart_include_outputs", bool(e.value)),
        )

    n_eval = estimate_eval_count(session.scan_cart_nx, session.scan_cart_ny)
    ui.label(
        f"Frozen evaluator calls: {n_eval} (one per grid cell; intent lenses reuse the same truth)."
    ).classes("text-caption q-mb-xs")
    ui.label(
        f"Projection: {SCAN_VAR_LABELS.get(session.scan_cart_x_key, session.scan_cart_x_key)} "
        f"vs {SCAN_VAR_LABELS.get(session.scan_cart_y_key, session.scan_cart_y_key)}"
    ).classes("text-caption text-grey")

    if session.scan_running:
        ui.linear_progress(value=session.scan_progress, show_value=True).classes("w-full")
        if session.scan_progress_text:
            ui.label(session.scan_progress_text).classes("text-caption")

    async def _run_quick() -> None:
        if session.scan_running:
            ui.notify("Scan already running", type="warning")
            return
        if session.scan_cart_x_key == session.scan_cart_y_key:
            ui.notify("Pick two different axes for X and Y.", type="negative")
            return
        xl = session.scan_cart_x_lo if session.scan_cart_x_lo is not None else x_lo_def
        xh = session.scan_cart_x_hi if session.scan_cart_x_hi is not None else x_hi_def
        yl = session.scan_cart_y_lo if session.scan_cart_y_lo is not None else y_lo_def
        yh = session.scan_cart_y_hi if session.scan_cart_y_hi is not None else y_hi_def
        session.scan_running = True
        session.scan_progress_text = "Quick probe (11×11)…"
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
                nx=11,
                ny=11,
                intents=list(session.scan_cart_intents or ["Reactor"]),
                include_outputs=bool(session.scan_cart_include_outputs),
                base_override=session.scan_cart_base_override,
            )
            session.scan_cartography_report = rep
            ui.notify("Quick probe complete — review Map & Probe or run full grid.", type="positive")
            if on_scan_complete:
                on_scan_complete()
        except Exception as exc:
            ui.notify(f"Quick probe failed: {exc}", type="negative")
        finally:
            session.scan_running = False
            session.scan_progress_text = ""

    async def _run_scan() -> None:
        if session.scan_running:
            ui.notify("Scan already running", type="warning")
            return
        if session.scan_cart_x_key == session.scan_cart_y_key:
            ui.notify("Pick two different axes for X and Y.", type="negative")
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

    with ui.row().classes("gap-2 q-mt-sm"):
        ui.button("Quick probe (11×11)", icon="speed", on_click=_run_quick).props("outline")
        btn = ui.button("Run cartography scan", icon="play_arrow", on_click=_run_scan).props("color=primary")
    if session.scan_running:
        btn.props("disable")
