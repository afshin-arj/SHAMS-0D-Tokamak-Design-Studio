"""Control Room Chronicle instruments — Phase 18."""
from __future__ import annotations

from pathlib import Path

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.decks.control_room import certified_search, knob_trade_space
from ui_nicegui.lib.control_room_helpers import CHRONICLE_TABS, report_to_json_bytes
from ui_nicegui.lib.cr_artifacts_helpers import collect_session_artifacts
from ui_nicegui.lib.cr_chronicle_helpers import (
    analyze_interval_narrowing,
    feasibility_map_grid,
    flatten_certified_search_artifact,
    list_variable_registry_keys,
    load_study_index,
    point_inputs_from_artifact,
    run_local_forensics,
    run_sensitivity_pack,
    sensitivity_table_rows,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_chronicle(session: DesignSession) -> None:
    if session.cr_chronicle_tab not in CHRONICLE_TABS:
        session.cr_chronicle_tab = CHRONICLE_TABS[0]

    ui.toggle(
        CHRONICLE_TABS,
        value=session.cr_chronicle_tab,
        on_change=lambda e: (
            setattr(session, "cr_chronicle_tab", str(e.value)),
            _panel.refresh(),
        ),
    ).classes("q-mb-md")

    _panel(session)


@ui.refreshable
def _panel(session: DesignSession) -> None:
    tab = session.cr_chronicle_tab
    if tab == "Variable Registry":
        _variable_registry()
    elif tab == "Sensitivity Explorer":
        _sensitivity(session)
    elif tab == "Feasibility Map":
        _feasibility_map(session)
    elif tab == "Knob Trade-Space":
        knob_trade_space.render_knob_trade_space(session)
    elif tab == "Certified Search":
        certified_search.render_certified_search(session)
    elif tab == "Interval Narrowing":
        _interval_narrowing(session)
    elif tab == "Local Forensics":
        _local_forensics(session)
    else:
        _study_dashboard(session)


def _variable_registry() -> None:
    ui.label("Variable Registry").classes("text-subtitle1")
    keys = list_variable_registry_keys()
    ui.label(f"{len(keys)} registered input keys (schema defaults).").classes("text-caption")
    with ui.expansion("Input keys", icon="list").classes("w-full"):
        for k in keys:
            ui.label(k).classes("text-caption")


def _artifact_for_chronicle(session: DesignSession) -> dict | None:
    if isinstance(session.cr_selected_artifact, dict):
        return session.cr_selected_artifact
    arts = collect_session_artifacts(session)
    if arts:
        return arts[-1]["artifact"]
    return None


def _sensitivity(session: DesignSession) -> None:
    ui.label("Sensitivity Explorer").classes("text-subtitle1")
    ui.label(
        "PHYS-KPI-001: jacobians of Q / H98 / Pfus / P_net on an INFEASIBLE artifact baseline are diagnostic residue."
    ).classes("text-caption text-orange q-mb-xs")
    art = _artifact_for_chronicle(session)
    if not isinstance(art, dict):
        empty_state("Load a run artifact (Artifacts section) or evaluate in Point Designer.", kind="info")
        from ui_nicegui.components.deck_gate import pd_prerequisite_gate

        pd_prerequisite_gate("Open Point Designer to evaluate a baseline for sensitivity.")
        return
    try:
        base = point_inputs_from_artifact(art)
    except Exception as exc:
        ui.label(f"Could not build PointInputs: {exc}").classes("text-negative")
        return

    knob_defaults = ["Ip_MA", "fG", "Bt_T", "R0_m", "a_m", "kappa", "Paux_MW", "Ti_keV"]
    available = [k for k in knob_defaults if hasattr(base, k)]
    knobs = ui.select(available, label="Knobs", value=available[:2], multiple=True).classes("w-full")
    outputs = ui.select(
        ["Q_DT_eqv", "H98", "Pfus_total_MW", "beta_N", "P_e_net_MW", "q95_proxy", "TBR"],
        label="Outputs",
        value=["Q_DT_eqv", "H98"],
        multiple=True,
    ).classes("w-full")
    step = ui.number("Step size (relative)", value=1e-3, format="%.6f")

    async def _run() -> None:
        ks = list(knobs.value) if knobs.value else []
        outs = list(outputs.value) if outputs.value else []
        if not ks or not outs:
            ui.notify("Select knobs and outputs", type="warning")
            return
        try:
            pack = await run.io_bound(
                run_sensitivity_pack,
                base,
                knobs=ks,
                outputs=outs,
                step_rel=float(step.value or 1e-3),
            )
            session.cr_sensitivity_last = pack
            session.cr_sensitivity_knobs = ks
            session.cr_sensitivity_outputs = outs
            ui.notify("Sensitivity pack ready", type="positive")
            _sens_view.refresh()
        except Exception as exc:
            ui.notify(f"Sensitivity failed: {exc}", type="negative")

    ui.button("Compute sensitivity pack", icon="insights", on_click=_run).props("outline")
    _sens_view(session)


@ui.refreshable
def _sens_view(session: DesignSession) -> None:
    pack = session.cr_sensitivity_last
    if not isinstance(pack, dict):
        return
    ks = session.cr_sensitivity_knobs or []
    outs = session.cr_sensitivity_outputs or []
    from ui_nicegui.lib.sensitivity_honesty import base_output_table_rows
    from ui_nicegui.lib.verdict_core import verdict_summary

    art = _artifact_for_chronicle(session)
    out = (art.get("outputs") if isinstance(art, dict) else None) or {}
    if not isinstance(out, dict) or not out:
        out = pack.get("base_outputs") if isinstance(pack.get("base_outputs"), dict) else {}
    feasible = bool(verdict_summary(out if isinstance(out, dict) else {}).get("feasible"))
    if not feasible:
        ui.label(
            "Baseline INFEASIBLE — claim-KPI jacobians and base values shown as diagnostic (PHYS-KPI-001)."
        ).classes("text-caption text-orange q-mb-xs")
    base_rows = base_output_table_rows(
        pack,
        outs,
        feasible=feasible,
        point_out=out if isinstance(out, dict) else None,
        design_intent=str(getattr(session, "design_intent", "") or ""),
    )
    if base_rows:
        ui.label("Baseline outputs (pack)").classes("text-caption")
        ui.table(
            columns=[
                {"name": "output", "label": "Output", "field": "output", "align": "left"},
                {"name": "value", "label": "Value", "field": "value"},
            ],
            rows=base_rows,
            row_key="output",
        ).classes("w-full q-mb-sm")
    rows = sensitivity_table_rows(pack, ks, outs, feasible=feasible)
    if rows:
        ui.table(
            columns=[
                {"name": "output", "label": "Output", "field": "output", "align": "left"},
                {"name": "knob", "label": "Knob", "field": "knob"},
                {"name": "jacobian", "label": "d(out)/d(knob)", "field": "jacobian"},
            ],
            rows=rows,
            row_key="output",
        ).classes("w-full")
    ui.button(
        "Download sensitivity JSON",
        icon="download",
        on_click=lambda: ui.download(report_to_json_bytes(pack), "sensitivity_pack.json"),
    ).props("flat outline")


def _feasibility_map(session: DesignSession) -> None:
    ui.label("Feasibility Map").classes("text-subtitle1")
    path_in = ui.input("Study index.json path", value=session.cr_study_index_path or "").classes("w-full")

    async def _load() -> None:
        p = Path(str(path_in.value or ""))
        if not p.is_file():
            ui.notify("Path not found", type="warning")
            return
        try:
            idx = await run.io_bound(load_study_index, p)
            session.cr_study_index = idx
            session.cr_study_index_path = str(p)
            ui.notify("Study index loaded", type="positive")
            _map_view.refresh()
        except Exception as exc:
            ui.notify(f"Load failed: {exc}", type="negative")

    ui.button("Load study index", on_click=_load).props("outline")
    _map_view(session)


@ui.refreshable
def _map_view(session: DesignSession) -> None:
    idx = session.cr_study_index
    if not isinstance(idx, dict):
        return
    cases = idx.get("cases") or []
    if not isinstance(cases, list) or len(cases) < 2:
        ui.label("Need cases in study index.").classes("text-caption")
        return
    in_cols = [k for k in cases[0].keys() if str(k).startswith("in_")]
    if len(in_cols) < 2:
        ui.label("Need at least two in_* columns for a 2D map.").classes("text-caption")
        return
    xcol = in_cols[0]
    ycol = in_cols[1]
    grid = feasibility_map_grid(cases, xcol, ycol)
    kpi_row([
        ("Cases", str(grid.get("n_cases", "-"))),
        ("X", xcol),
        ("Y", ycol),
    ])
    with ui.expansion("Feasibility grid JSON", icon="grid_on").classes("w-full"):
        render_json_blob(grid)


def _interval_narrowing(session: DesignSession) -> None:
    ui.label("Interval Narrowing & Repair").classes("text-subtitle1")
    art = session.v340_cert_search_last
    if not isinstance(art, dict):
        empty_state(
            "Requires a **Certified Search** artifact. Run **Chronicle → Certified Search** or upload JSON.",
            kind="info",
        )
        return
    variables, records = flatten_certified_search_artifact(art)
    n_pass = sum(1 for r in records if str(r.get("verdict", "")).upper() == "PASS")
    kpi_row([("Candidates", str(len(records))), ("PASS", str(n_pass))])

    async def _analyze() -> None:
        try:
            ev = await run.io_bound(analyze_interval_narrowing, variables, records)
            session.v343_interval_narrowing_evidence = ev
            ui.notify("Interval narrowing complete", type="positive")
            _narrow_view.refresh()
        except Exception as exc:
            ui.notify(f"Analysis failed: {exc}", type="negative")

    ui.button("Analyze candidate set", icon="build", on_click=_analyze).props("outline")
    _narrow_view(session)


@ui.refreshable
def _narrow_view(session: DesignSession) -> None:
    ev = session.v343_interval_narrowing_evidence
    if isinstance(ev, dict):
        with ui.expansion("Narrowing evidence", icon="description").classes("w-full"):
            render_json_blob(ev)


def _local_forensics(session: DesignSession) -> None:
    ui.label("Local Forensics").classes("text-subtitle1")
    intent = ui.select(["Reactor", "Research"], label="Design intent", value="Reactor")

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        locked, task, is_owner = runlock_status("ControlRoom")
        if locked:
            ui.notify(
                f"Busy: {task} — wait or force-clear from Helm."
                if not is_owner
                else "Control Room already holds the run lock.",
                type="warning",
            )
            return
        if not runlock_acquire("Control Room: Local forensics", "ControlRoom"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        try:
            rep = await run.io_bound(
                run_local_forensics,
                session.build_point_inputs(),
                design_intent=str(intent.value),
            )
            session.cr_forensics_last = rep
            ui.notify("Forensics complete", type="positive")
            _forensics_view.refresh()
        except Exception as exc:
            ui.notify(f"Forensics failed: {exc}", type="negative")
        finally:
            runlock_release("ControlRoom")

    ui.button("Run local sensitivity forensics", icon="search", on_click=_run).props("outline")
    _forensics_view(session)


@ui.refreshable
def _forensics_view(session: DesignSession) -> None:
    rep = session.cr_forensics_last
    if isinstance(rep, dict):
        with ui.expansion("Forensics report", icon="bug_report").classes("w-full"):
            render_json_blob(rep)


def _study_dashboard(session: DesignSession) -> None:
    ui.label("Study Dashboard").classes("text-subtitle1")
    cap = session.active_study_capsule
    rep = session.trade_last
    if isinstance(cap, dict):
        kpi_row([
            ("Capsule id", str(cap.get("id", "-"))),
            ("Records", str(len(cap.get("records") or []))),
            ("Pareto", str(len(cap.get("pareto") or []))),
        ])
    elif isinstance(rep, dict):
        summary = rep.get("summary") or {}
        kpi_row([
            ("Samples", str(summary.get("n_samples", "-"))),
            ("Feasible", str(summary.get("n_feasible", "-"))),
            ("Pareto", str(summary.get("n_pareto", "-"))),
        ])
    else:
        empty_state("No active study capsule or trade study — run Trade Study Studio first.", kind="info")
