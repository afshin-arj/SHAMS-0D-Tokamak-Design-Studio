"""Sensitivity Lab — perturbation + local finite-difference views."""
from __future__ import annotations

import math

from nicegui import run, ui

from ui_nicegui.decks.point_designer.forensics import render_forensics
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.pd_parity_helpers import (
    PERT_SCAN_PARAMS,
    baseline_delta_rows,
    fmt_num,
    local_fd_sensitivity_rows,
    run_perturbation_scan,
)
from ui_nicegui.session import DesignSession

_PERT_KNOBS = PERT_SCAN_PARAMS


def render_sensitivity_lab(session: DesignSession) -> None:
    out = session.pd_last_outputs or session.last_eval
    if not isinstance(out, dict):
        return

    ui.label("Parameter sensitivity").classes("text-subtitle1")
    ui.label("Local probes around the cached baseline — diagnostic only, not optimization.").classes(
        "text-caption"
    )

    with ui.expansion("Delta view — compare to baseline", icon="compare_arrows").classes("w-full"):
        ui.label("Set a baseline (e.g., preset or previous run) and view KPI deltas.").classes("text-caption")

        def _set_baseline() -> None:
            art = session.pd_last_artifact
            if isinstance(art, dict):
                session.pd_baseline_artifact = dict(art)
                ui.notify("Baseline set to current point.", type="positive")
                _delta_panel.refresh()

        ui.button("Set baseline = current point", on_click=_set_baseline).props("outline q-mb-sm")
        _delta_panel(session)

    with ui.expansion("Local sensitivities — finite difference", icon="functions").classes("w-full"):
        ui.label("Local derivatives around the current point (±0.1% central difference).").classes("text-caption")
        fd_area = ui.column().classes("w-full")

        async def _run_fd() -> None:
            from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

            locked, task, is_owner = runlock_status("PointDesigner")
            if locked and not is_owner:
                ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
                return
            if not runlock_acquire("Point Designer: Local FD", "PointDesigner"):
                ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
                return
            ui.notify("Computing local sensitivities…", type="info")
            try:
                base = session.build_point_inputs()

                def _eval(pi):
                    return ui_evaluate(pi, origin="NiceGUI:LocalFD", Paux_for_Q_MW=session.paux_for_q)

                rows = await run.io_bound(local_fd_sensitivity_rows, base, _eval)
                fd_area.clear()
                with fd_area:
                    if rows:
                        ui.table(
                            columns=[
                                {"name": "output", "label": "Output", "field": "output", "align": "left"},
                                {"name": "param", "label": "Param", "field": "param"},
                                {"name": "dY/dX", "label": "∂Y/∂X", "field": "dY/dX"},
                                {"name": "elasticity", "label": "Elasticity", "field": "elasticity"},
                            ],
                            rows=rows,
                            row_key="output",
                        ).classes("w-full")
                    else:
                        ui.label("Sensitivities unavailable for this point.").classes("text-caption")
            except Exception as exc:
                ui.notify(f"Sensitivity failed: {exc}", type="negative")
            finally:
                runlock_release("PointDesigner")

        ui.button("Compute local FD sensitivities", on_click=_run_fd).classes("q-mt-sm")

    with ui.expansion("Perturbation scan (±10%, 8 params)", icon="science").classes("w-full"):
        ui.label(
            "Perturb key inputs by ±10% and report which hard constraints flip. Local intuition, not optimization."
        ).classes("text-caption")
        scan_area = ui.column().classes("w-full")

        async def _scan() -> None:
            from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

            locked, task, is_owner = runlock_status("PointDesigner")
            if locked and not is_owner:
                ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
                return
            if not runlock_acquire("Point Designer: Perturbation scan", "PointDesigner"):
                ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
                return
            ui.notify("Running perturbation scan…", type="info")
            try:
                base = session.build_point_inputs()

                def _eval(pi):
                    return ui_evaluate(pi, origin="NiceGUI:PertScan", Paux_for_Q_MW=session.paux_for_q)

                rows = await run.io_bound(run_perturbation_scan, base, _eval)
                session.pd_pert_scan_rows = rows
                scan_area.clear()
                with scan_area:
                    if rows:
                        ui.table(
                            columns=[
                                {"name": "param", "label": "Param", "field": "param", "align": "left"},
                                {"name": "factor", "label": "Factor", "field": "factor"},
                                {"name": "value", "label": "Value", "field": "value"},
                                {"name": "hard_failed", "label": "Hard failed", "field": "hard_failed", "align": "left"},
                                {"name": "new_failures", "label": "New failures", "field": "new_failures", "align": "left"},
                                {"name": "resolved", "label": "Resolved", "field": "resolved", "align": "left"},
                            ],
                            rows=rows,
                            row_key="param",
                        ).classes("w-full")
                    else:
                        ui.label("No scan results.").classes("text-caption")
            except Exception as exc:
                ui.notify(f"Scan failed: {exc}", type="negative")
            finally:
                runlock_release("PointDesigner")

        ui.button("Run ±10% perturbation scan", on_click=_scan).classes("q-mt-sm")
        if session.pd_pert_scan_rows:
            with scan_area:
                ui.table(
                    columns=[
                        {"name": "param", "label": "Param", "field": "param", "align": "left"},
                        {"name": "factor", "label": "Factor", "field": "factor"},
                        {"name": "value", "label": "Value", "field": "value"},
                        {"name": "hard_failed", "label": "Hard failed", "field": "hard_failed", "align": "left"},
                        {"name": "new_failures", "label": "New failures", "field": "new_failures", "align": "left"},
                        {"name": "resolved", "label": "Resolved", "field": "resolved", "align": "left"},
                    ],
                    rows=session.pd_pert_scan_rows,
                    row_key="param",
                ).classes("w-full")

    with ui.expansion("Perturbation probe (single knob ±10%)", icon="tune").classes("w-full"):
        knob = ui.select(_PERT_KNOBS, label="Knob", value=_PERT_KNOBS[0]).classes("w-full")
        result_area = ui.column().classes("w-full")

        async def _probe() -> None:
            from dataclasses import asdict, replace

            from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

            locked, task, is_owner = runlock_status("PointDesigner")
            if locked and not is_owner:
                ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
                return
            if not runlock_acquire("Point Designer: Perturbation probe", "PointDesigner"):
                ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
                return
            base = session.build_point_inputs()
            base_dict = asdict(base) if hasattr(base, "__dataclass_fields__") else base.to_dict()
            k = str(knob.value)
            if k not in base_dict:
                runlock_release("PointDesigner")
                ui.notify(f"Knob {k} not in baseline.", type="warning")
                return
            try:
                x0 = float(base_dict[k])
            except (TypeError, ValueError):
                runlock_release("PointDesigner")
                ui.notify("Invalid baseline value.", type="negative")
                return
            try:
                rows = []
                for label, mult in (("-10%", 0.9), ("baseline", 1.0), ("+10%", 1.1)):
                    pi = replace(base, **{k: x0 * mult})
                    yo = await run.io_bound(
                        ui_evaluate, pi, origin="NiceGUI:PerturbationProbe", Paux_for_Q_MW=session.paux_for_q
                    )
                    q = yo.get("Q_DT_eqv", yo.get("Q"))
                    from ui_nicegui.lib.verdict_core import verdict_summary

                    feas = "yes" if verdict_summary(yo).get("feasible") else "no"
                    rows.append({"step": label, "knob": k, "value": f"{x0 * mult:.4g}", "Q": _fmt(q), "feasible": feas})
                result_area.clear()
                with result_area:
                    ui.table(
                        columns=[
                            {"name": "step", "label": "Step", "field": "step"},
                            {"name": "knob", "label": "Knob", "field": "knob"},
                            {"name": "value", "label": "Value", "field": "value"},
                            {"name": "Q", "label": "Q", "field": "Q"},
                            {"name": "feasible", "label": "Feasible", "field": "feasible"},
                        ],
                        rows=rows,
                        row_key="step",
                    ).classes("w-full")
            finally:
                runlock_release("PointDesigner")

        ui.button("Run ±10% probe", on_click=_probe).classes("q-mt-sm")

    ui.separator()
    render_forensics(session)


@ui.refreshable
def _delta_panel(session: DesignSession) -> None:
    base_art = session.pd_baseline_artifact
    cur_art = session.pd_last_artifact
    if isinstance(base_art, dict) and isinstance(cur_art, dict):
        rows = baseline_delta_rows(base_art, cur_art)
        ui.table(
            columns=[
                {"name": "KPI", "label": "KPI", "field": "KPI", "align": "left"},
                {"name": "baseline", "label": "Baseline", "field": "baseline"},
                {"name": "current", "label": "Current", "field": "current"},
                {"name": "delta", "label": "Delta", "field": "delta"},
                {"name": "unit", "label": "Unit", "field": "unit"},
            ],
            rows=rows,
            row_key="KPI",
        ).classes("w-full")
    else:
        ui.label("No baseline set yet.").classes("text-caption")


def _fmt(v) -> str:
    try:
        f = float(v)
        if math.isnan(f):
            return "nan"
        return f"{f:.4g}"
    except (TypeError, ValueError):
        return str(v)
