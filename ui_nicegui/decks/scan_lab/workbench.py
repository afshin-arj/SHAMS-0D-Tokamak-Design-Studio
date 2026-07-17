"""Scan Lab cartography workbench — map & probe (tab 2)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.compare_helpers import send_scan_probe_to_compare
from ui_nicegui.lib.scan_labels import WB_VIEW_KEYS, WB_VIEW_LABELS
from ui_nicegui.lib.scan_workbench_helpers import (
    SCAN_WB_VIEWS,
    apply_probe_to_session,
    build_point_grid,
    contour_field_keys,
    plotly_figure_for_view,
    probe_cell_summary,
)
from ui_nicegui.session import DesignSession


def _view_label(key: str) -> str:
    return WB_VIEW_LABELS.get(key, key)


def render_workbench(
    session: DesignSession,
    rep: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    intents = list(rep.get("intents") or session.scan_cart_intents or ["Reactor"])
    if not intents:
        intents = ["Reactor"]
    if session.scan_wb_intent not in intents:
        session.scan_wb_intent = str(intents[0])
    if session.scan_wb_view not in SCAN_WB_VIEWS:
        session.scan_wb_view = SCAN_WB_VIEWS[0]

    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    if not x_vals or not y_vals:
        empty_state("Scan report has no grid — re-run cartography.", kind="warning")
        return

    session.scan_wb_i = max(0, min(int(session.scan_wb_i), len(x_vals) - 1))
    session.scan_wb_j = max(0, min(int(session.scan_wb_j), len(y_vals) - 1))

    ui.label("Map & probe").classes("text-subtitle1")
    ui.label("Orient → look → probe. PASS = blocking-feasible; gray dominance = all cells feasible.").classes(
        "text-caption text-grey q-mb-sm"
    )
    ui.markdown(
        f"Slice: **{rep.get('x_key')}** vs **{rep.get('y_key')}** · "
        f"intents: **{' / '.join(str(i) for i in intents)}** · n={int(rep.get('n_points') or 0)}"
    ).classes("text-caption q-mb-md")

    with ui.row().classes("w-full items-start gap-4"):
        with ui.column().classes("flex-none").style("min-width: 220px; max-width: 280px"):
            _render_nav(session, rep, intents, on_update)
        with ui.column().classes("flex-grow"):
            _render_map(session, rep, intents)
        with ui.column().classes("flex-none").style("min-width: 260px; max-width: 340px"):
            _render_inspector(session, rep, intents, on_update)


def _render_nav(
    session: DesignSession,
    rep: dict,
    intents: list,
    on_update: Optional[Callable[[], None]],
) -> None:
    ui.label("Navigate").classes("text-subtitle2")

    def _changed() -> None:
        if on_update:
            on_update()

    ui.select(
        intents,
        label="Primary intent",
        value=session.scan_wb_intent,
        on_change=lambda e: (setattr(session, "scan_wb_intent", str(e.value)), _changed()),
    ).props("dense").classes("w-full")

    ui.select(
        WB_VIEW_KEYS,
        label="Map view",
        value=session.scan_wb_view,
        on_change=lambda e: (setattr(session, "scan_wb_view", str(e.value)), _changed()),
    ).props("dense").classes("w-full")
    ui.label(_view_label(session.scan_wb_view)).classes("text-caption text-grey q-mb-sm")

    if str(session.scan_wb_view).startswith("Operating"):
        keys = contour_field_keys(rep)
        if not keys:
            ui.markdown("Re-run with **Include compact outputs** on Setup & Run.").classes(
                "text-caption text-orange"
            )
        else:
            if session.scan_wb_contour_field not in keys:
                session.scan_wb_contour_field = keys[0]
            ui.select(
                keys,
                label="Contour field",
                value=session.scan_wb_contour_field,
                on_change=lambda e: (
                    setattr(session, "scan_wb_contour_field", str(e.value)),
                    _changed(),
                ),
            ).props("dense").classes("w-full")

    if len(intents) >= 2:
        ui.checkbox(
            "Compare intents side-by-side",
            value=session.scan_wb_compare_intents,
            on_change=lambda e: (
                setattr(session, "scan_wb_compare_intents", bool(e.value)),
                _changed(),
            ),
        )

    with ui.expansion("Legend", icon="info").classes("w-full"):
        ui.label(
            "Dominant limiter map: color = worst blocking constraint. "
            "Robustness map: local p-feasible proxy (not the KPI verdict band)."
        ).classes("text-caption")
        try:
            from ui_nicegui.lib.scan_workbench_helpers import dominance_labels

            labs = dominance_labels(rep, session.scan_wb_intent)
            ui.label(", ".join(labs[:12])).classes("text-caption")
            if labs == ["PASS"]:
                ui.label("All cells feasible — map is neutral gray by design.").classes(
                    "text-caption text-grey"
                )
        except Exception:
            pass


@ui.refreshable
def _render_map(session: DesignSession, rep: dict, intents: list) -> None:
    view = session.scan_wb_view
    out_key = session.scan_wb_contour_field if str(view).startswith("Operating") else None

    if session.scan_wb_compare_intents and len(intents) >= 2:
        with ui.row().classes("w-full gap-2"):
            for it in intents[:2]:
                with ui.column().classes("flex-1"):
                    ui.label(str(it)).classes("text-caption text-center")
                    try:
                        fig = plotly_figure_for_view(rep, str(it), view, out_key=out_key)
                        ui.plotly(fig).classes("w-full")
                    except Exception as exc:
                        ui.label(f"Map unavailable: {exc}").classes("text-caption text-negative")
    else:
        try:
            fig = plotly_figure_for_view(rep, session.scan_wb_intent, view, out_key=out_key)
            ui.plotly(fig).classes("w-full")
        except Exception as exc:
            ui.label(f"Map unavailable: {exc}").classes("text-caption text-negative")

    ui.label("Use Inspector to probe (i, j) and read the constraint stack.").classes(
        "text-caption text-grey q-mt-xs"
    )


@ui.refreshable
def _render_inspector(
    session: DesignSession,
    rep: dict,
    intents: list,
    on_update: Optional[Callable[[], None]],
) -> None:
    ui.label("Probe / inspector").classes("text-subtitle2")
    x_vals = rep.get("x_vals") or []
    y_vals = rep.get("y_vals") or []
    grid = build_point_grid(rep)

    def _probe_changed() -> None:
        _render_inspector.refresh()
        _render_map.refresh()
        if on_update:
            on_update()

    ui.slider(
        min=0,
        max=max(0, len(x_vals) - 1),
        step=1,
        value=session.scan_wb_i,
        on_change=lambda e: (setattr(session, "scan_wb_i", int(e.value)), _probe_changed()),
    ).props("label").classes("w-full")
    ui.label(f"i (x) = {session.scan_wb_i} · x ≈ {x_vals[session.scan_wb_i] if x_vals else '-'}").classes(
        "text-caption"
    )
    ui.slider(
        min=0,
        max=max(0, len(y_vals) - 1),
        step=1,
        value=session.scan_wb_j,
        on_change=lambda e: (setattr(session, "scan_wb_j", int(e.value)), _probe_changed()),
    ).props("label").classes("w-full")
    ui.label(f"j (y) = {session.scan_wb_j} · y ≈ {y_vals[session.scan_wb_j] if y_vals else '-'}").classes(
        "text-caption q-mb-sm"
    )

    cell = grid.get((session.scan_wb_i, session.scan_wb_j))
    if not cell:
        empty_state("Selected cell not found in grid.", kind="warning")
        return

    if session.scan_wb_compare_intents and len(intents) >= 2:
        for it in intents[:2]:
            _render_probe_block(session, rep, grid, str(it))
            ui.separator()
    else:
        _render_probe_block(session, rep, grid, session.scan_wb_intent)

    with ui.expansion("Promote cell → Point Designer", icon="upload").classes("w-full"):
        ui.label("Copies scan base + probed x/y into Point Designer inputs (no auto-evaluate).").classes(
            "text-caption"
        )

        def _promote() -> None:
            apply_probe_to_session(session, rep, cell)
            session.scan_promote_note = f"Scan probe ({session.scan_wb_i},{session.scan_wb_j})"
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer

            navigate_to_point_designer(session)
            ui.notify("Opened Point Designer Configure with probed cell inputs.", type="positive")

        ui.button("Promote to Point Designer", on_click=_promote).props("outline")

    def _send_compare(slot: str) -> None:
        try:
            send_scan_probe_to_compare(session, rep, cell, slot, label="Scan Lab probe")
            ui.notify(f"Sent probed cell to Compare slot {slot}", type="positive")
        except Exception as exc:
            ui.notify(f"Compare handoff failed: {exc}", type="negative")

    with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
        ui.button("Send probe → Compare A", icon="compare", on_click=lambda: _send_compare("A")).props("flat outline")
        ui.button("Send probe → Compare B", icon="compare", on_click=lambda: _send_compare("B")).props("flat outline")
        from ui_nicegui.lib.compare_helpers import open_compare_deck

        ui.button("Open Compare deck", icon="compare_arrows", on_click=lambda: open_compare_deck(session)).props(
            "flat outline"
        )

    ui.markdown("For causality / UQ tools, use the **Interpret** tab.").classes(
        "text-caption text-grey q-mt-sm"
    )


def _render_probe_block(session: DesignSession, rep: dict, grid: dict, intent: str) -> None:
    summary = probe_cell_summary(grid, rep, intent, session.scan_wb_i, session.scan_wb_j)
    ui.label(f"Intent: {intent}").classes("text-subtitle2")
    ui.markdown(
        f"- Blocking feasible: **{summary.get('blocking_feasible')}**\n"
        f"- Dominant limiter: **{summary.get('dominant_blocking') or '-'}**\n"
        f"- Min blocking margin: **{summary.get('min_blocking_margin') or '-'}**\n"
        f"- Cell robustness label: **{summary.get('robustness') or '-'}**"
    ).classes("text-body2")
    perf = summary.get("performance") or {}
    if perf:
        bits = []
        for k, v in perf.items():
            try:
                bits.append(f"{k}={float(v):.4g}")
            except (TypeError, ValueError):
                bits.append(f"{k}={v}")
        ui.label("Operating point: " + ", ".join(bits)).classes("text-caption q-mb-xs")
    failed = summary.get("failed_blocking") or []
    if failed:
        with ui.expansion("Failed blocking constraints", icon="warning").classes("w-full"):
            for name in failed:
                ui.label(str(name)).classes("text-caption")
    margins = summary.get("margin_rows") or []
    if margins:
        with ui.expansion("Hard margins (worst first)", icon="table_chart").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "constraint", "label": "Constraint", "field": "constraint", "align": "left"},
                    {"name": "margin_frac", "label": "Margin", "field": "margin_frac"},
                ],
                rows=margins,
                row_key="constraint",
            ).classes("w-full")
    fo = summary.get("failure_order") or []
    if fo:
        with ui.expansion("Failure order (hard, worst-first)", icon="list").classes("w-full"):
            for item in fo:
                ui.label(str(item)).classes("text-caption")
