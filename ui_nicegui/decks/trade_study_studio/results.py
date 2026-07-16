"""Trade Study results tables and exports."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.trade_study_helpers import report_to_json_bytes
from ui_nicegui.session import DesignSession


def render_study_results(session: DesignSession, rep: dict) -> None:
    summary = rep.get("summary") or {}
    records = rep.get("records") or []
    feasible = rep.get("feasible") or []
    pareto = rep.get("pareto") or []
    objectives = (rep.get("meta") or {}).get("objectives") or []

    if not records:
        ui.label("No samples in this run.").classes("text-orange")
        return

    if not feasible and not pareto:
        ui.label("No feasible points in sampled bounds.").classes("text-orange")
        _render_blocking_hint(records)

    if len(objectives) >= 2 and pareto:
        _render_pareto_plot(pareto, objectives[0], objectives[1])

    fam = rep.get("family_summary") or {}
    fam_rows = fam.get("rows") if isinstance(fam, dict) else None
    if isinstance(fam_rows, list) and fam_rows:
        with ui.expansion("Design family summary", icon="category").classes("w-full"):
            ui.table(
                columns=[
                    {"name": "family", "label": "Family", "field": "family", "align": "left"},
                    {"name": "title", "label": "Title", "field": "title"},
                    {"name": "n", "label": "N", "field": "n"},
                    {"name": "n_feasible", "label": "Feasible", "field": "n_feasible"},
                    {"name": "feasible_frac", "label": "Feasible frac", "field": "feasible_frac"},
                ],
                rows=[r for r in fam_rows if isinstance(r, dict)][:20],
                row_key="family",
            ).classes("w-full")

    _render_table("All samples", records[:100], objectives)
    if feasible:
        _render_table("Feasible samples", feasible[:100], objectives)
    if pareto:
        _render_table("Feasible Pareto subset", pareto[:100], objectives)
        _render_promote(session, pareto, rep)

    ui.separator()
    data = report_to_json_bytes(rep)
    ui.button(
        "Download study report (JSON)",
        icon="download",
        on_click=lambda: ui.download(data, "shams_trade_study.json"),
    ).props("outline")
    if session.active_study_capsule:
        cap = report_to_json_bytes(session.active_study_capsule)
        ui.button(
            "Download study capsule (JSON)",
            icon="download",
            on_click=lambda: ui.download(cap, "shams_study_capsule.json"),
        ).props("outline flat")


def _render_blocking_hint(records: list[dict]) -> None:
    counts: dict[str, int] = {}
    for row in records:
        if row.get("is_feasible"):
            continue
        dom = str(row.get("dominant_constraint") or "(unknown)")
        counts[dom] = counts.get(dom, 0) + 1
    if not counts:
        return
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
    with ui.expansion("Top blocking constraints", icon="block").classes("w-full"):
        for name, n in top:
            ui.markdown(f"- **{name}**: {n}")


def _render_pareto_plot(pareto: list[dict], x_key: str, y_key: str) -> None:
    try:
        import plotly.express as px
    except ImportError:
        return
    xs = [p.get(x_key) for p in pareto]
    ys = [p.get(y_key) for p in pareto]
    colors = [str(p.get("design_family") or p.get("dominant_constraint") or "") for p in pareto]
    fig = px.scatter(
        x=xs,
        y=ys,
        color=colors if any(colors) else None,
        title="Feasible Pareto subset",
        labels={"x": x_key, "y": y_key},
    )
    fig.update_layout(height=360, margin=dict(l=40, r=20, t=40, b=40))
    with ui.expansion("Pareto scatter", icon="scatter_plot").classes("w-full"):
        ui.plotly(fig).classes("w-full")


def _render_table(title: str, rows: list[dict], objectives: list[str]) -> None:
    if not rows:
        return
    cols = ["i", "is_feasible", "dominant_constraint", "min_margin_frac"]
    cols += [c for c in objectives if c in rows[0]][:4]
    cols += [c for c in ("design_family", "R0_m", "Bt_T", "Ip_MA") if c in rows[0] and c not in cols]
    table_rows = []
    for r in rows:
        table_rows.append({k: r.get(k) for k in cols if k in r})
    with ui.expansion(title, icon="table_chart").classes("w-full"):
        ui.table(
            columns=[{"name": k, "label": k, "field": k} for k in cols if table_rows and k in table_rows[0]],
            rows=table_rows,
            row_key="i",
        ).classes("w-full")


def _render_promote(session: DesignSession, pareto: list[dict], rep: dict) -> None:
    bounds = (rep.get("meta") or {}).get("bounds") or {}
    bound_keys = [k for k in bounds if isinstance(bounds.get(k), (list, tuple))]
    with ui.expansion("Promote Pareto point to Point Designer", icon="upload").classes("w-full"):
        idx = ui.number("Row index", value=0, min=0, max=max(len(pareto) - 1, 0), step=1)

        def _promote() -> None:
            i = int(idx.value or 0)
            if i < 0 or i >= len(pareto):
                ui.notify("Invalid row index", type="warning")
                return
            row = pareto[i]
            for k in bound_keys:
                if k in row and row[k] is not None:
                    try:
                        session.inputs[k] = float(row[k])
                    except (TypeError, ValueError):
                        pass
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer

            navigate_to_point_designer(session)
            ui.notify("Opened Point Designer Configure with study inputs.", type="positive")

        ui.button("Promote to Point Designer", on_click=_promote).props("outline")
