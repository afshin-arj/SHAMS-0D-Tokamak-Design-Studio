"""Scan Lab cartography workbench — dominance maps, probe, causality, families, atlas (Phase 13)."""
from __future__ import annotations

import json
from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.scan_helpers import report_to_json_bytes
from ui_nicegui.lib.scan_workbench_helpers import (
    SCAN_WB_VIEWS,
    apply_probe_to_session,
    build_atlas_pdf_bytes,
    build_design_families,
    build_point_grid,
    certify_design_families,
    contour_field_keys,
    design_family_table_rows,
    families_json_bytes,
    plotly_figure_for_view,
    probe_cell_summary,
    run_causality_trace,
)
from ui_nicegui.session import DesignSession


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

    ui.label("Cartography workbench").classes("text-subtitle1")
    ui.label(
        "Orient → look → probe → explain. Cartography/interpretability only — no optimization."
    ).classes("text-caption text-grey q-mb-sm")
    ui.label(
        f"Projection: **{rep.get('x_key')}** vs **{rep.get('y_key')}** · "
        f"intents: **{' / '.join(str(i) for i in intents)}** · n={int(rep.get('n_points') or 0)}"
    ).classes("text-caption q-mb-md")

    with ui.row().classes("w-full items-start gap-4"):
        with ui.column().classes("flex-none").style("min-width: 220px; max-width: 280px"):
            _render_nav(session, rep, intents, on_update)
        with ui.column().classes("flex-grow"):
            _render_map(session, rep, intents)
        with ui.column().classes("flex-none").style("min-width: 260px; max-width: 340px"):
            _render_inspector(session, rep, intents, on_update)

    ui.separator().classes("q-my-md")
    _render_design_families(session, rep, intents, on_update)
    _render_export_panel(session, rep, intents)


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
        SCAN_WB_VIEWS,
        label="View",
        value=session.scan_wb_view,
        on_change=lambda e: (setattr(session, "scan_wb_view", str(e.value)), _changed()),
    ).props("dense").classes("w-full")

    if str(session.scan_wb_view).startswith("Operating"):
        keys = contour_field_keys(rep)
        if not keys:
            ui.label("Re-run scan with **Include outputs** for contour fields.").classes(
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
            "Compare intents (side-by-side)",
            value=session.scan_wb_compare_intents,
            on_change=lambda e: (
                setattr(session, "scan_wb_compare_intents", bool(e.value)),
                _changed(),
            ),
        )

    with ui.expansion("Legend / meaning", icon="info").classes("w-full"):
        ui.label(
            "PASS = blocking-feasible. Failures colored by dominant blocking constraint (worst margin)."
        ).classes("text-caption")
        try:
            from ui_nicegui.lib.scan_workbench_helpers import dominance_labels

            labs = dominance_labels(rep, session.scan_wb_intent)
            ui.label(", ".join(labs[:12])).classes("text-caption")
            if labs == ["PASS"]:
                ui.label("All cells feasible — dominance map is neutral/gray.").classes(
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

    ui.label("Use the Inspector to probe a cell and inspect the constraint stack.").classes(
        "text-caption text-grey q-mt-xs"
    )


@ui.refreshable
def _render_inspector(
    session: DesignSession,
    rep: dict,
    intents: list,
    on_update: Optional[Callable[[], None]],
) -> None:
    ui.label("Probe / Inspector").classes("text-subtitle2")
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
    ui.label(f"i (x index) = {session.scan_wb_i} · x ≈ {x_vals[session.scan_wb_i] if x_vals else '-'}").classes(
        "text-caption"
    )
    ui.slider(
        min=0,
        max=max(0, len(y_vals) - 1),
        step=1,
        value=session.scan_wb_j,
        on_change=lambda e: (setattr(session, "scan_wb_j", int(e.value)), _probe_changed()),
    ).props("label").classes("w-full")
    ui.label(f"j (y index) = {session.scan_wb_j} · y ≈ {y_vals[session.scan_wb_j] if y_vals else '-'}").classes(
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

    with ui.expansion("Promote probed cell to Point Designer", icon="upload").classes("w-full"):
        ui.label("Copies scan base + probed x/y into Point Designer inputs (no auto-evaluate).").classes(
            "text-caption"
        )

        def _promote() -> None:
            apply_probe_to_session(session, rep, cell)
            ui.notify("Promoted to Point Designer — switch deck to evaluate.", type="positive")

        ui.button("Promote to Point Designer", on_click=_promote).props("outline")

    _render_causality_panel(session, rep, grid)


def _render_probe_block(session: DesignSession, rep: dict, grid: dict, intent: str) -> None:
    summary = probe_cell_summary(grid, rep, intent, session.scan_wb_i, session.scan_wb_j)
    ui.label(f"Intent: {intent}").classes("text-subtitle2")
    ui.markdown(
        f"- blocking_feasible: **{summary.get('blocking_feasible')}**\n"
        f"- dominant_blocking: **{summary.get('dominant_blocking') or '-'}**\n"
        f"- min_blocking_margin: **{summary.get('min_blocking_margin') or '-'}**\n"
        f"- robustness: **{summary.get('robustness') or '-'}**"
    ).classes("text-body2")
    failed = summary.get("failed_blocking") or []
    if failed:
        with ui.expansion("Failed blocking constraints", icon="warning").classes("w-full"):
            for name in failed:
                ui.label(str(name)).classes("text-caption")
    margins = summary.get("margin_rows") or []
    if margins:
        with ui.expansion("Hard-constraint margins (worst first)", icon="table_chart").classes("w-full"):
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


def _render_causality_panel(session: DesignSession, rep: dict, grid: dict) -> None:
    with ui.expansion("Causality trace", icon="account_tree").classes("w-full q-mt-sm"):
        ui.label(
            "Local finite-difference sensitivity for the dominant blocking constraint at this cell."
        ).classes("text-caption")
        step = ui.slider(
            min=0.005,
            max=0.05,
            step=0.005,
            value=session.scan_causality_rel_step,
            on_change=lambda e: setattr(session, "scan_causality_rel_step", float(e.value)),
        ).props("label")
        ui.label(f"Relative step: {session.scan_causality_rel_step:.3f}").classes("text-caption")

        async def _run_causality() -> None:
            ui.notify("Computing causality trace…", type="info")
            try:
                tr = await run.io_bound(
                    run_causality_trace,
                    session.build_point_inputs(),
                    rep,
                    intent=session.scan_wb_intent,
                    i=session.scan_wb_i,
                    j=session.scan_wb_j,
                    rel_step=float(session.scan_causality_rel_step),
                )
                session.scan_causality_last = tr
                ui.notify("Causality trace complete.", type="positive")
                _causality_results.refresh()
            except Exception as exc:
                ui.notify(f"Causality failed: {exc}", type="negative")

        ui.button("Compute causality trace", icon="play_arrow", on_click=_run_causality).props(
            "outline dense"
        )
        _causality_results(session)


@ui.refreshable
def _causality_results(session: DesignSession) -> None:
    tr = session.scan_causality_last
    if not isinstance(tr, dict):
        return
    if tr.get("status") == "skipped":
        ui.label(str(tr.get("reason") or "Skipped")).classes("text-caption text-grey")
        return
    drivers = tr.get("drivers") or []
    if drivers:
        rows = [
            {
                "knob": d.get("knob"),
                "d_margin_d_knob": d.get("d_margin_d_knob"),
                "margin_delta_plus": d.get("margin_delta_plus"),
            }
            for d in drivers
            if isinstance(d, dict)
        ]
        ui.table(
            columns=[
                {"name": "knob", "label": "Knob", "field": "knob", "align": "left"},
                {"name": "d_margin_d_knob", "label": "d(margin)/d(knob)", "field": "d_margin_d_knob"},
                {"name": "margin_delta_plus", "label": "Δ+ margin", "field": "margin_delta_plus"},
            ],
            rows=rows,
            row_key="knob",
        ).classes("w-full q-mt-sm")


def _render_design_families(
    session: DesignSession,
    rep: dict,
    intents: list,
    on_update: Optional[Callable[[], None]],
) -> None:
    with ui.expansion("Design family governance (v394)", icon="hub").classes("w-full"):
        ui.label(
            "Deterministic design families from cartography (regime-signature labeling + connected components)."
        ).classes("text-caption q-mb-sm")
        it_sel = session.scan_df_intent if session.scan_df_intent in intents else str(intents[0])
        ui.select(
            intents,
            label="Intent lens",
            value=it_sel,
            on_change=lambda e: setattr(session, "scan_df_intent", str(e.value)),
        ).props("dense").classes("w-full q-mb-sm")
        ui.slider(
            min=4,
            max=80,
            step=1,
            value=session.scan_df_min_points,
            on_change=lambda e: setattr(session, "scan_df_min_points", int(e.value)),
        ).props("label").classes("w-full")
        ui.label(f"Minimum points per family: {session.scan_df_min_points}").classes("text-caption")

        async def _build() -> None:
            ui.notify("Building design families…", type="info")
            try:
                art = await run.io_bound(
                    build_design_families,
                    rep,
                    intent=str(session.scan_df_intent or it_sel),
                    min_points=int(session.scan_df_min_points),
                )
                session.scan_design_families_v394 = art
                session.scan_design_families_v394_cert = certify_design_families(art)
                ui.notify(
                    f"Built {len(art.get('families') or [])} families.",
                    type="positive",
                )
                _families_table.refresh()
            except Exception as exc:
                ui.notify(f"Family build failed: {exc}", type="negative")

        with ui.row().classes("gap-2"):
            ui.button("Build families", icon="build", on_click=_build).props("outline")
            ui.button(
                "Clear",
                on_click=lambda: (
                    setattr(session, "scan_design_families_v394", None),
                    setattr(session, "scan_design_families_v394_cert", None),
                    _families_table.refresh(),
                ),
            ).props("flat")

        _families_table(session)


@ui.refreshable
def _families_table(session: DesignSession) -> None:
    art = session.scan_design_families_v394
    if not isinstance(art, dict) or art.get("families") is None:
        ui.label("No design family artifact yet — run Build families after a scan.").classes(
            "text-caption text-grey q-mt-sm"
        )
        return
    cert = session.scan_design_families_v394_cert
    if isinstance(cert, dict):
        ui.label(f"Certification verdict: {cert.get('verdict', 'UNKNOWN')}").classes("text-caption")
    rows = design_family_table_rows(art)
    if rows:
        ui.table(
            columns=[
                {"name": "family_id", "label": "ID", "field": "family_id"},
                {"name": "label", "label": "Label", "field": "label", "align": "left"},
                {"name": "n_points", "label": "n", "field": "n_points"},
                {"name": "feasible_frac", "label": "Feasible frac", "field": "feasible_frac"},
                {"name": "x_range", "label": "x range", "field": "x_range"},
                {"name": "y_range", "label": "y range", "field": "y_range"},
            ],
            rows=rows,
            row_key="family_id",
        ).classes("w-full q-mt-sm")
    ui.button(
        "Download families JSON",
        icon="download",
        on_click=lambda: ui.download(families_json_bytes(art), "shams_scan_design_families_v394.json"),
    ).props("outline flat q-mt-sm")


def _render_export_panel(session: DesignSession, rep: dict, intents: list) -> None:
    with ui.expansion("Trust & export", icon="download").classes("w-full"):
        ui.markdown(
            f"- n_points: **{rep.get('n_points')}**\n"
            f"- run_seconds: **{rep.get('run_seconds', '-')}**\n"
            f"- report_id: **{rep.get('id', '-')}**"
        ).classes("text-body2")
        ui.button(
            "Download cartography report (JSON)",
            icon="download",
            on_click=lambda: ui.download(report_to_json_bytes(rep), "shams_cartography_report.json"),
        ).props("outline").classes("q-mr-sm")
        art = session.scan_cartography_artifact
        if isinstance(art, dict):
            art_bytes = json.dumps(art, indent=2, default=str).encode("utf-8")

            ui.button(
                "Download scan artifact (JSON)",
                icon="download",
                on_click=lambda b=art_bytes: ui.download(b, "shams_scan_artifact_v1.json"),
            ).props("outline flat")

        ui.separator().classes("q-my-sm")
        ui.label("Reference atlas (PDF) — one page per intent (dominance map).").classes("text-caption")
        ui.input(
            "Atlas title",
            value=session.scan_atlas_title,
            on_change=lambda e: setattr(session, "scan_atlas_title", str(e.value or "")),
        ).classes("w-full")

        async def _build_atlas() -> None:
            ui.notify("Building atlas PDF…", type="info")
            try:
                pdf = await run.io_bound(
                    build_atlas_pdf_bytes,
                    rep,
                    intents,
                    title=session.scan_atlas_title or "SHAMS — Scan Lab Atlas",
                )
                session.scan_atlas_pdf_bytes = pdf
                ui.notify("Atlas PDF ready.", type="positive")
                _atlas_download.refresh()
            except Exception as exc:
                ui.notify(f"Atlas build failed: {exc}", type="negative")

        ui.button("Build atlas PDF", icon="picture_as_pdf", on_click=_build_atlas).props("outline")
        _atlas_download(session)
        ui.label(
            "Signature Atlas (10-page builder) deferred — use Streamlit for full signature export."
        ).classes("text-caption text-grey q-mt-sm")


@ui.refreshable
def _atlas_download(session: DesignSession) -> None:
    pdf = session.scan_atlas_pdf_bytes
    if isinstance(pdf, (bytes, bytearray)) and len(pdf) > 100:
        ui.button(
            "Download atlas (PDF)",
            icon="download",
            on_click=lambda: ui.download(bytes(pdf), "shams_scan_atlas.pdf"),
        ).props("color=primary flat q-mt-sm")
