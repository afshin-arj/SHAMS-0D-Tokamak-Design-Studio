"""Dominance Compass + Closure Trace telemetry."""
from __future__ import annotations

import math

from nicegui import ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_dominance_closure(session: DesignSession) -> None:
    ui.label("Authority dominance & closures").classes("text-subtitle1")
    ui.label(
        "Read-only decision telemetry: what limits this point, and how the closure converged."
    ).classes("text-caption q-mb-sm")

    art = session.pd_last_artifact
    if not isinstance(art, dict):
        empty_state("Run **Evaluate Point** first.", kind="info")
        return

    cons0 = art.get("constraints") or []
    led0 = art.get("constraint_ledger") or {}
    solver0 = art.get("solver") or {}

    with ui.tabs().classes("w-full") as tabs:
        t_dom = ui.tab("Dominance Compass")
        t_closure = ui.tab("Closure Trace")

    with ui.tab_panels(tabs, value=t_dom).classes("w-full"):
        with ui.tab_panel(t_dom):
            _render_dominance_compass(led0, cons0)
        with ui.tab_panel(t_closure):
            _render_closure_trace(solver0)


def _render_dominance_compass(led0: dict, cons0: list) -> None:
    top = led0.get("top_blockers") if isinstance(led0, dict) else []
    if isinstance(top, list) and top:
        ui.label("Dominant violated constraints (hard-weighted)").classes("text-subtitle2")
        rows = []
        for e in top[:12]:
            if not isinstance(e, dict):
                continue
            rows.append({
                "rank": e.get("dominance_rank"),
                "name": e.get("name"),
                "group": e.get("group"),
                "severity": e.get("severity"),
                "margin_frac": e.get("margin_frac"),
                "value": e.get("value"),
                "limit": e.get("limit"),
            })
        ui.table(
            columns=[
                {"name": "rank", "label": "Rank", "field": "rank"},
                {"name": "name", "label": "Name", "field": "name", "align": "left"},
                {"name": "group", "label": "Group", "field": "group"},
                {"name": "severity", "label": "Severity", "field": "severity"},
                {"name": "margin_frac", "label": "Margin frac", "field": "margin_frac"},
            ],
            rows=rows,
            row_key="name",
        ).classes("w-full")
    else:
        ui.label("No violated hard constraints — hard-feasible under the frozen evaluator.").classes(
            "text-positive"
        )

    hard = [c for c in (cons0 or []) if isinstance(c, dict) and str(c.get("severity", "hard")).lower() == "hard"]

    def _mf(c: dict) -> float:
        try:
            return float(c.get("margin_frac", float("nan")))
        except (TypeError, ValueError):
            return float("nan")

    hard2 = [c for c in hard if math.isfinite(_mf(c))]
    hard2.sort(key=_mf)
    if hard2:
        ui.label("Tightest hard constraints (active set, worst-first)").classes("text-subtitle2 q-mt-md")
        rows2 = []
        for c in hard2[:12]:
            rows2.append({
                "name": c.get("name"),
                "passed": bool(c.get("passed", True)),
                "margin_frac": _mf(c),
                "value": c.get("value"),
                "limit": c.get("limit"),
            })
        ui.table(
            columns=[
                {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                {"name": "passed", "label": "Pass", "field": "passed"},
                {"name": "margin_frac", "label": "Margin frac", "field": "margin_frac"},
                {"name": "value", "label": "Value", "field": "value"},
                {"name": "limit", "label": "Limit", "field": "limit"},
            ],
            rows=rows2,
            row_key="name",
        ).classes("w-full")


def _render_closure_trace(solver0: dict) -> None:
    ui.label("Closure ledger (solver trace)").classes("text-subtitle2")
    if not (isinstance(solver0, dict) and solver0.get("backend") and isinstance(solver0.get("trace"), list)):
        empty_state(
            "No solver trace for this run (direct evaluation without target solve, or legacy path).",
            kind="info",
        )
        return

    tr = solver0.get("trace") or []
    rows = []
    for k, step in enumerate(tr[:200]):
        if not isinstance(step, dict):
            continue
        row = {"iter": k}
        for kk in ("x", "vars", "residual_norm", "target_errors", "status", "note", "clamped", "alpha", "damping"):
            if kk in step:
                row[kk] = step.get(kk)
        rows.append(row)

    if rows:
        cols = [{"name": "iter", "label": "Iter", "field": "iter"}]
        for kk in ("residual_norm", "status", "note", "alpha", "damping"):
            if any(kk in r for r in rows):
                cols.append({"name": kk, "label": kk, "field": kk, "align": "left"})
        ui.table(columns=cols, rows=rows, row_key="iter").classes("w-full")
    else:
        render_json_blob(tr[:20])

    ui.label(
        f"backend={solver0.get('backend')} • ok={solver0.get('ok')} • "
        f"iters={solver0.get('iters')} • message={solver0.get('message')}"
    ).classes("text-caption q-mt-sm")
