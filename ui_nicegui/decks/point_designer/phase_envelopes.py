"""Phase Envelopes sub-deck — NiceGUI Phase 11."""
from __future__ import annotations

import json
from pathlib import Path

from nicegui import run, ui

from ui_nicegui.bootstrap import repo_root
from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.components.kpi_row import kpi_row
from ui_nicegui.lib.artifact_access import get_point_artifact_triple
from ui_nicegui.lib.pd_outer_loop_helpers import (
    DEFAULT_PHASES_JSON,
    VAR_GROUPS,
    field_group,
    filter_fields_by_group,
    make_point_inputs,
    numeric_point_fields,
    parse_phases_json,
    phase_table_rows,
)
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob

try:
    from src.phase_envelopes import run_phase_envelope_for_point
    from tools.phase_envelopes import export_phase_envelope_zip
except ImportError:
    from phase_envelopes import run_phase_envelope_for_point  # type: ignore
    from tools.phase_envelopes import export_phase_envelope_zip  # type: ignore


def render_phase_envelopes(session: DesignSession, *, ui_key_prefix: str = "pd_phase_env", embedded: bool = False) -> None:
    if not embedded:
        ui.label("Phase Envelopes").classes("text-h6")
        ui.label(
            "Ordered quasi-static phases (ramp/flat-top/ramp-down). Each phase is evaluated "
            "independently with frozen truth. Worst-phase determines the envelope verdict."
        ).classes("text-caption q-mb-sm")
    else:
        ui.label(
            "Each phase evaluated independently; worst phase sets the envelope verdict."
        ).classes("text-caption q-mb-sm")

    art, point_inp, _ = get_point_artifact_triple(session)
    if not isinstance(point_inp, dict):
        empty_state("Run **Point Designer → Truth Console → Evaluate Point** first.", kind="info")
        return

    base_inputs = make_point_inputs(point_inp)
    if not session.phase_envelopes_phases_json:
        session.phase_envelopes_phases_json = DEFAULT_PHASES_JSON

    _render_phase_cockpit(session, point_inp)

    ui.label("Phase specification (JSON)").classes("text-subtitle2")
    ui.label(
        "Authoritative phase spec for execution and export. Overrides map to PointInputs fields."
    ).classes("text-caption")

    phases_area = ui.textarea(
        label="Phases JSON",
        value=session.phase_envelopes_phases_json,
    ).classes("w-full").props("rows=10")

    def _sync_json() -> None:
        session.phase_envelopes_phases_json = phases_area.value or DEFAULT_PHASES_JSON

    phases_area.on("update:model-value", lambda: _sync_json())

    async def _run() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        _sync_json()
        if getattr(session, "phase_envelopes_running", False):
            ui.notify("Phase envelope already running", type="warning")
            return
        locked, task, is_owner = runlock_status("PointDesigner")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Point Designer: Phase envelopes", "PointDesigner"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        session.phase_envelopes_running = True
        ui.notify("Running phase envelope…", type="info")
        try:
            phases = parse_phases_json(session.phase_envelopes_phases_json)
            prefix = session.phase_envelopes_label_prefix or "phase"
            env = await run.io_bound(
                run_phase_envelope_for_point,
                base_inputs,
                phases,
                label_prefix=prefix,
            )
            session.phase_envelopes_last = env
            ui.notify("Phase envelope complete.", type="positive")
            _results.refresh()
        except Exception as exc:
            ui.notify(f"Phase envelope failed: {exc}", type="negative")
        finally:
            session.phase_envelopes_running = False
            runlock_release("PointDesigner")

    with ui.row().classes("w-full gap-4 items-end q-mt-sm"):
        ui.input(
            "Label prefix",
            value=session.phase_envelopes_label_prefix,
            on_change=lambda e: setattr(session, "phase_envelopes_label_prefix", str(e.value)),
        ).classes("flex-1")
        ui.button("Run Phase Envelope", icon="play_arrow", on_click=_run).props("color=primary")

    _results(session)


def _render_phase_cockpit(session: DesignSession, point_inp: dict) -> None:
    try:
        parsed = json.loads(session.phase_envelopes_phases_json or DEFAULT_PHASES_JSON)
    except Exception:
        parsed = []
    phase_names = [str(p.get("name")) for p in parsed if isinstance(p, dict) and p.get("name")]
    if not phase_names:
        phase_names = ["ramp_up", "flat_top", "ramp_down"]

    numeric_fields, other_fields = numeric_point_fields(point_inp)
    all_fields = numeric_fields + other_fields
    override_state: dict[str, dict[str, float]] = {pn: {} for pn in phase_names}

    with ui.expansion("Phase cockpit editor (writes JSON)", icon="tune", value=False).classes("w-full q-mb-sm"):
        ui.label(
            "Structured per-phase overrides — updates the JSON spec below without touching frozen truth."
        ).classes("text-caption q-mb-sm")
        grp = ui.select(VAR_GROUPS, label="Variable group", value="PLASMA").classes("w-full")
        candidates = filter_fields_by_group(all_fields, str(grp.value or "PLASMA"))
        sel = ui.select(candidates, label="Override variables", value=[], multiple=True).classes("w-full")
        cols_container = ui.column().classes("w-full")

        def _render_phase_cols() -> None:
            cols_container.clear()
            with cols_container:
                vars_pick = list(sel.value or [])
                if not vars_pick:
                    ui.label("Select override variables above.").classes("text-caption")
                    return
                with ui.row().classes("w-full gap-2"):
                    for pn in phase_names:
                        with ui.column().classes("flex-1"):
                            ui.label(pn).classes("text-subtitle2")
                            for k in vars_pick:
                                base_v = point_inp.get(k)
                                if isinstance(base_v, (int, float)):
                                    def _set(ph: str, key: str, e) -> None:
                                        override_state.setdefault(ph, {})[key] = float(e.value)

                                    ui.number(
                                        k,
                                        value=float(base_v),
                                        on_change=lambda e, ph=pn, key=k: _set(ph, key, e),
                                    ).classes("w-full")

        sel.on("update:model-value", lambda: _render_phase_cols())
        _render_phase_cols()

        def _sync_from_cockpit() -> None:
            spec = []
            for pn in phase_names:
                base_phase = next((p for p in parsed if isinstance(p, dict) and p.get("name") == pn), {})
                spec.append(
                    {
                        "name": pn,
                        "input_overrides": dict(override_state.get(pn) or {}),
                        "policy_overrides": dict(base_phase.get("policy_overrides") or {}),
                        "notes": str(base_phase.get("notes") or "Quasi-static check (no dynamics)."),
                    }
                )
            session.phase_envelopes_phases_json = json.dumps(spec, indent=2, sort_keys=True)
            ui.notify("Phase JSON updated from cockpit.", type="positive")

        ui.button("Update JSON from cockpit", icon="sync", on_click=_sync_from_cockpit).props("outline q-mt-sm")


@ui.refreshable
def _results(session: DesignSession) -> None:
    env = session.phase_envelopes_last
    if not isinstance(env, dict):
        ui.label("No phase envelope results yet.").classes("text-caption text-grey q-mt-md")
        return

    summ = env.get("envelope_summary") if isinstance(env.get("envelope_summary"), dict) else {}
    ui.label("Envelope verdict").classes("text-subtitle2 q-mt-md")
    kpi_row([
        ("Verdict", str(summ.get("envelope_verdict", "UNKNOWN"))),
        ("Worst phase", str(summ.get("worst_phase", ""))),
        ("Worst hard margin", str(summ.get("worst_phase_worst_hard_margin_frac", ""))),
    ])

    with ui.expansion("Envelope summary (JSON)").classes("w-full"):
        render_json_blob(summ)

    rows = phase_table_rows(env)
    if rows:
        ui.label("Phase table").classes("text-subtitle2 q-mt-sm")
        ui.table(
            columns=[
                {"name": "phase", "label": "Phase", "field": "phase", "align": "left"},
                {"name": "feasible", "label": "Feasible", "field": "feasible"},
                {"name": "n_hard_failed", "label": "Hard failed", "field": "n_hard_failed"},
                {"name": "worst_hard", "label": "Worst hard", "field": "worst_hard"},
                {"name": "worst_margin", "label": "Worst margin", "field": "worst_margin"},
            ],
            rows=rows,
            row_key="phase",
        ).classes("w-full")

    async def _export_zip() -> None:
        try:
            out_dir = Path(repo_root()) / "ui_runs" / "phase_envelopes"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_zip = out_dir / "phase_envelopes.zip"
            await run.io_bound(export_phase_envelope_zip, env, out_zip)
            data = out_zip.read_bytes()
            ui.download(data, out_zip.name)
            ui.notify("Phase envelope ZIP ready.", type="positive")
        except Exception as exc:
            ui.notify(f"Export failed: {exc}", type="negative")

    ui.button("Export Phase Envelopes ZIP", icon="archive", on_click=_export_zip).props("outline q-mt-sm")
