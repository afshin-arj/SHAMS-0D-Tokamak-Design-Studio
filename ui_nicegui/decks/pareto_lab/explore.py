"""Pareto Lab — Explore Frontier tab (interactive plot + table)."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from ui_nicegui.lib.pareto_helpers import FOCUS_METRIC_KEYS, OBJ_CATALOG, metric_label
from ui_nicegui.lib.pareto_interpret_helpers import enrich_pareto_front, failure_atlas_points, robust_filtered
from ui_nicegui.lib.pareto_labels import QUESTION_PRESETS, ROBUST_MARGIN_HELP
from ui_nicegui.session import DesignSession


def render_explore_tab(
    session: DesignSession,
    pareto_last: dict,
    *,
    on_update: Optional[Callable[[], None]] = None,
) -> None:
    pareto = pareto_last.get("pareto") or []
    feasible = pareto_last.get("feasible") or []
    objectives = pareto_last.get("objectives") or {}
    obj_keys = list(objectives.keys())
    all_samples = pareto_last.get("all") or []

    if not pareto and not feasible:
        ui.label("No feasible points — adjust bounds or intent on **Setup & Run**.").classes("text-orange")
        return

    plot_keys = obj_keys + [k for k in ("R0_m", "Bt_T", "Ip_MA", "fG") if k not in obj_keys]
    if not plot_keys:
        plot_keys = ["R0_m", "P_e_net_MW"]

    if session.pareto_plot_x not in plot_keys:
        session.pareto_plot_x = obj_keys[0] if obj_keys else plot_keys[0]
    if session.pareto_plot_y not in plot_keys:
        session.pareto_plot_y = obj_keys[1] if len(obj_keys) > 1 else plot_keys[min(1, len(plot_keys) - 1)]

    ui.label("Frontier plot").classes("text-subtitle2")
    ui.label("Gray = infeasible shadow · Color = dominant constraint on Pareto points").classes("text-caption")
    ui.markdown(ROBUST_MARGIN_HELP).classes("text-caption text-grey q-mb-xs")

    preset_labels = list(QUESTION_PRESETS.keys())
    if preset_labels:
        def _apply_preset(e) -> None:
            cfg = QUESTION_PRESETS.get(str(e.value), {})
            if cfg.get("plot_x"):
                session.pareto_plot_x = str(cfg["plot_x"])
            if cfg.get("plot_y"):
                session.pareto_plot_y = str(cfg["plot_y"])
            if cfg.get("color"):
                session.pareto_plot_color = str(cfg["color"])
            if cfg.get("robust_only"):
                session.pareto_robust_only = True
            if cfg.get("intent_split"):
                session.pareto_intent_split = True
            if cfg.get("show_failures"):
                session.pareto_show_failures = True
            if on_update:
                on_update()

        ui.select(preset_labels, label="Quick exploration lens", on_change=_apply_preset).classes("w-full q-mb-sm")

    focus_opts = [k for k in FOCUS_METRIC_KEYS if any(k in p for p in (pareto + feasible))]
    if not getattr(session, "pareto_focus_metrics", None):
        session.pareto_focus_metrics = [k for k in ("Q_DT_eqv", "H98", "TBR") if k in focus_opts]
    ui.select(
        focus_opts or FOCUS_METRIC_KEYS,
        label="Focus metrics (table + hover)",
        value=[k for k in (session.pareto_focus_metrics or []) if k in (focus_opts or FOCUS_METRIC_KEYS)],
        multiple=True,
        on_change=lambda e: setattr(session, "pareto_focus_metrics", list(e.value or [])),
    ).classes("w-full q-mb-sm")

    with ui.row().classes("w-full gap-2 items-end"):
        x_sel = ui.select(plot_keys, label="X axis", value=session.pareto_plot_x).classes("flex-1")
        y_sel = ui.select(plot_keys, label="Y axis", value=session.pareto_plot_y).classes("flex-1")
        color_opts = [
            "dominant_constraint",
            "intent",
            "geography",
            "segment_id",
            "confidence",
            "mirage_flag_v402",
            "(none)",
        ] + obj_keys
        c_val = session.pareto_plot_color if session.pareto_plot_color in color_opts else "dominant_constraint"
        c_sel = ui.select(color_opts, label="Color", value=c_val).classes("flex-1")
        robust_sw = ui.switch(
            "Show only margin-robust",
            value=session.pareto_robust_only,
        ).classes("flex-none")
        overlay_sw = ui.switch(
            "Highlight margin-robust overlay",
            value=getattr(session, "pareto_robust_overlay", True),
        ).classes("flex-none")
        mirage_sw = ui.switch(
            "Hide mirages",
            value=bool(getattr(session, "pareto_hide_mirages", False)),
        ).classes("flex-none")
        intent_sw = ui.switch(
            "Split Reactor / Research traces",
            value=getattr(session, "pareto_intent_split", False),
        ).classes("flex-none")
        fail_sw = ui.switch("Show failure atlas", value=session.pareto_show_failures).classes("flex-none")

    def _sync() -> None:
        session.pareto_plot_x = str(x_sel.value)
        session.pareto_plot_y = str(y_sel.value)
        session.pareto_plot_color = str(c_sel.value)
        session.pareto_robust_only = bool(robust_sw.value)
        session.pareto_robust_overlay = bool(overlay_sw.value)
        session.pareto_hide_mirages = bool(mirage_sw.value)
        session.pareto_intent_split = bool(intent_sw.value)
        session.pareto_show_failures = bool(fail_sw.value)
        if on_update:
            on_update()

    for w in (x_sel, y_sel, c_sel):
        w.on("update:model-value", lambda: _sync())
    robust_sw.on("update:model-value", lambda: _sync())
    overlay_sw.on("update:model-value", lambda: _sync())
    mirage_sw.on("update:model-value", lambda: _sync())
    intent_sw.on("update:model-value", lambda: _sync())
    fail_sw.on("update:model-value", lambda: _sync())

    x_key, y_key = session.pareto_plot_x, session.pareto_plot_y
    thr = float(pareto_last.get("robust_margin_thr") or session.pareto_robust_margin_thr or 0.1)
    full_pareto = list(pareto)
    robust_subset = robust_filtered(full_pareto, thr)
    plot_pareto = robust_subset if session.pareto_robust_only else full_pareto
    if getattr(session, "pareto_hide_mirages", False):
        plot_pareto = [p for p in plot_pareto if not bool(p.get("mirage_flag_v402"))]
        robust_subset = [p for p in robust_subset if not bool(p.get("mirage_flag_v402"))]
    enriched = enrich_pareto_front(
        plot_pareto, feasible, x_key=x_key, y_key=y_key, robust_margin_thr=thr,
    )
    pareto_last["pareto_enriched"] = enriched
    color_key = str(session.pareto_plot_color)
    if color_key in ("geography", "segment_id", "confidence"):
        plot_src = enriched
    else:
        plot_src = plot_pareto
    intent_split = bool(getattr(session, "pareto_intent_split", False)) or str(
        pareto_last.get("intent_mode") or ""
    ).startswith("Both")
    _render_plot(
        plot_src if color_key != "(none)" else plot_pareto,
        x_key,
        y_key,
        color_key,
        failure_pts=failure_atlas_points(all_samples, x_key, y_key) if session.pareto_show_failures else [],
        focus_keys=list(session.pareto_focus_metrics or []),
        robust_highlight=robust_subset if session.pareto_robust_overlay and not session.pareto_robust_only else [],
        intent_split=intent_split,
    )

    ui.separator().classes("q-my-sm")
    _render_table(enriched or plot_pareto or pareto, obj_keys, list(session.pareto_focus_metrics or []))


def _render_plot(
    pareto: list[dict],
    x_key: str,
    y_key: str,
    color_key: str,
    *,
    failure_pts: list[dict],
    focus_keys: list[str],
    robust_highlight: list[dict] | None = None,
    intent_split: bool = False,
) -> None:
    if not pareto and not failure_pts:
        ui.label("Nothing to plot.").classes("text-caption")
        return
    try:
        import plotly.graph_objects as go
    except ImportError:
        ui.label("Plotly not available.").classes("text-orange")
        return

    fig = go.Figure()
    if failure_pts:
        fig.add_trace(
            go.Scatter(
                x=[p.get(x_key) for p in failure_pts],
                y=[p.get(y_key) for p in failure_pts],
                mode="markers",
                name="Infeasible",
                marker=dict(color="rgba(160,160,160,0.35)", size=5),
                hovertext=[p.get("first_failure") for p in failure_pts],
            )
        )
    if pareto:
        if intent_split:
            for intent_name, color in (("Reactor", "#1976d2"), ("Research", "#e65100")):
                subset = [p for p in pareto if str(p.get("intent", "")).startswith(intent_name[:4])]
                if not subset:
                    continue
                _add_pareto_trace(fig, subset, x_key, y_key, color_key, focus_keys, name=intent_name, default_color=color)
        else:
            _add_pareto_trace(fig, pareto, x_key, y_key, color_key, focus_keys, name="Pareto")
        if robust_highlight:
            fig.add_trace(
                go.Scatter(
                    x=[p.get(x_key) for p in robust_highlight],
                    y=[p.get(y_key) for p in robust_highlight],
                    mode="markers",
                    name="Margin-robust",
                    marker=dict(size=12, symbol="x", color="#2e7d32", line=dict(width=2)),
                )
            )
    xu = OBJ_CATALOG.get(x_key, {}).get("units", "-")
    yu = OBJ_CATALOG.get(y_key, {}).get("units", "-")
    fig.update_layout(
        height=420,
        margin=dict(l=48, r=20, t=36, b=48),
        xaxis_title=metric_label(x_key) if x_key in OBJ_CATALOG else f"{x_key} [{xu}]",
        yaxis_title=metric_label(y_key) if y_key in OBJ_CATALOG else f"{y_key} [{yu}]",
        legend=dict(orientation="h"),
    )
    ui.plotly(fig).classes("w-full")


def _add_pareto_trace(
    fig,
    pareto: list[dict],
    x_key: str,
    y_key: str,
    color_key: str,
    focus_keys: list[str],
    *,
    name: str = "Pareto",
    default_color: str = "#1976d2",
) -> None:
    import plotly.graph_objects as go

    colors = None
    if color_key and color_key != "(none)":
        colors = [str(p.get(color_key) or "") for p in pareto]
    hover_lines = []
    for p in pareto:
        parts = [f"dom: {p.get('dominant_constraint')}", f"margin: {p.get('min_constraint_margin')}"]
        if p.get("intent"):
            parts.append(f"intent: {p.get('intent')}")
        if bool(p.get("mirage_flag_v402")):
            parts.append("MIRAGE")
        for fk in focus_keys:
            if fk in p and p[fk] is not None:
                parts.append(f"{fk}: {p[fk]}")
        hover_lines.append("<br>".join(parts))
    fig.add_trace(
        go.Scatter(
            x=[p.get(x_key) for p in pareto],
            y=[p.get(y_key) for p in pareto],
            mode="markers",
            name=name,
            marker=dict(size=9, color=colors if colors and any(colors) else default_color),
            hovertext=hover_lines,
            hoverinfo="text",
        )
    )


def _render_table(pareto: list[dict], obj_keys: list[str], focus_keys: list[str]) -> None:
    extra = [k for k in focus_keys if k not in obj_keys]
    cols = [
        "intent",
        "mirage_flag_v402",
        "dominant_constraint",
        "min_constraint_margin",
        "geography",
        "freedom_left",
        "segment_id",
        "confidence",
    ] + obj_keys[:8] + extra[:6]
    rows = []
    for i, p in enumerate(pareto[:80]):
        row = {"idx": i}
        for c in cols:
            if c == "mirage_flag_v402":
                row[c] = "YES" if bool(p.get("mirage_flag_v402")) else ""
            elif c in p:
                row[c] = p[c]
        rows.append(row)
    if not rows:
        return
    ui.label(f"Pareto table ({len(pareto)} points, showing {len(rows)})").classes("text-subtitle2")
    col_names = ["idx"] + [c for c in cols if c in rows[0]]
    ui.table(
        columns=[{"name": k, "label": metric_label(k) if k in OBJ_CATALOG else k, "field": k, "align": "left"} for k in col_names],
        rows=rows,
        row_key="idx",
        pagination={"rowsPerPage": 15},
    ).classes("w-full")
