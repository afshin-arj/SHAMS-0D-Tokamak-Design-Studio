"""Pareto Lab results — frontier plot and exports (Batch 5)."""
from __future__ import annotations

import csv
import io

from nicegui import ui

from ui_nicegui.lib.pareto_helpers import OBJ_CATALOG, artifact_to_json_bytes, build_pareto_artifact
from ui_nicegui.session import DesignSession


def render_pareto_results(session: DesignSession, pareto_last: dict) -> None:
    pareto = pareto_last.get("pareto") or []
    feasible = pareto_last.get("feasible") or []
    objectives = pareto_last.get("objectives") or {}

    if not pareto and not feasible:
        ui.label("No feasible or Pareto points in this run.").classes("text-orange")
        _render_failure_hint(pareto_last)
        return

    if not pareto:
        ui.label(
            "Feasible designs exist but no non-dominated Pareto set was produced "
            "(objective redundancy or insufficient variation)."
        ).classes("text-orange")
        ui.label(f"Feasible points: {len(feasible)}").classes("text-caption")

    if pareto:
        ui.label("Pareto front (constraint-annotated)").classes("text-subtitle2 q-mt-sm")
        obj_keys = list(objectives.keys())
        if len(obj_keys) >= 2:
            x_key, y_key = obj_keys[0], obj_keys[1]
            _render_frontier_plot(pareto, x_key, y_key)
        _render_pareto_table(pareto, obj_keys)
        _render_promote_handoff(session, pareto, pareto_last)

    ui.separator()
    _render_exports(pareto_last)


def _render_failure_hint(pareto_last: dict) -> None:
    samples = pareto_last.get("all") or []
    if not samples:
        return
    counts: dict[str, int] = {}
    for row in samples:
        if row.get("is_feasible"):
            continue
        ff = str(row.get("first_failure") or "(unknown)")
        counts[ff] = counts.get(ff, 0) + 1
    if not counts:
        return
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
    with ui.expansion("Top blocking constraints (sampled)", icon="block").classes("w-full"):
        for name, n in top:
            ui.markdown(f"- **{name}**: {n} samples")


def _render_frontier_plot(pareto: list[dict], x_key: str, y_key: str) -> None:
    try:
        import plotly.express as px
    except ImportError:
        return
    xs = [p.get(x_key) for p in pareto]
    ys = [p.get(y_key) for p in pareto]
    colors = [str(p.get("dominant_constraint") or "") for p in pareto]
    fig = px.scatter(
        x=xs,
        y=ys,
        color=colors if any(colors) else None,
        labels={
            "x": f"{x_key} [{OBJ_CATALOG.get(x_key, {}).get('units', '-')}]",
            "y": f"{y_key} [{OBJ_CATALOG.get(y_key, {}).get('units', '-')}]",
        },
        title="Pareto front",
    )
    fig.update_layout(height=380, margin=dict(l=40, r=20, t=40, b=40))
    ui.plotly(fig).classes("w-full")


def _render_pareto_table(pareto: list[dict], obj_keys: list[str]) -> None:
    cols = ["intent", "dominant_constraint", "min_constraint_margin"] + obj_keys[:6]
    rows = []
    for i, p in enumerate(pareto[:50]):
        row = {"idx": i}
        for c in cols:
            if c in p:
                row[c] = p[c]
        rows.append(row)
    if not rows:
        return
    with ui.expansion("Pareto table (first 50)", icon="table_chart").classes("w-full"):
        ui.table(
            columns=[{"name": k, "label": k, "field": k} for k in ["idx"] + [c for c in cols if c in rows[0]]],
            rows=rows,
            row_key="idx",
        ).classes("w-full")


def _render_promote_handoff(session: DesignSession, pareto: list[dict], pareto_last: dict) -> None:
    bounds = pareto_last.get("bounds") or {}
    with ui.expansion("Promote Pareto point to Point Designer", icon="upload").classes("w-full"):
        ui.label("Select a front row to copy decision variables into Point Designer inputs (no auto-evaluate).").classes(
            "text-caption"
        )
        idx = ui.number("Row index", value=0, min=0, max=max(len(pareto) - 1, 0), step=1)

        def _promote() -> None:
            i = int(idx.value or 0)
            if i < 0 or i >= len(pareto):
                ui.notify("Invalid row index", type="warning")
                return
            row = pareto[i]
            for k in bounds:
                if k in row and row[k] is not None:
                    try:
                        session.inputs[k] = float(row[k])
                    except (TypeError, ValueError):
                        pass
            ui.notify("Promoted to Point Designer inputs — switch deck to evaluate.", type="positive")

        ui.button("Promote to Point Designer", on_click=_promote).props("outline")


def _render_exports(pareto_last: dict) -> None:
    artifact = build_pareto_artifact(pareto_last)
    json_bytes = artifact_to_json_bytes(artifact)
    ui.button(
        "Download Pareto artifact (JSON)",
        icon="download",
        on_click=lambda: ui.download(json_bytes, "shams_pareto_artifact.json"),
    ).props("outline")

    pareto = pareto_last.get("pareto") or []
    if pareto:
        csv_bytes = _pareto_csv_bytes(pareto)
        ui.button(
            "Download Pareto front (CSV)",
            icon="download",
            on_click=lambda: ui.download(csv_bytes, "shams_pareto_front.csv"),
        ).props("outline flat")


def _pareto_csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    keys = sorted({k for r in rows for k in r.keys()})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")
