"""Advanced tools — assumption lock, sensitivities, QA harness, artifact restore."""

from __future__ import annotations

import json

from nicegui import run, ui

from ui_nicegui.lib.systems_assumption_lock import assumption_settings_hash, check_assumption_lock
from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.session import DesignSession


def render_tools_panel(session: DesignSession) -> None:
    if not session.systems_expert_view:
        return

    with ui.expansion("Expert tools", icon="build").classes("w-full q-mt-sm"):
        ui.label("Assumption lock").classes("text-subtitle2")
        h = assumption_settings_hash(session)
        locked = session.systems_assumption_lock_hash
        ok, msg = check_assumption_lock(session)
        ui.label(f"Current hash: {h} | Locked: {locked or '(none)'}").classes("text-caption")
        if not ok and msg:
            ui.label(msg).classes("text-caption text-negative")

        def _capture_lock() -> None:
            session.systems_assumption_lock_hash = h
            ui.notify("Assumption lock captured", type="positive")

        def _clear_lock() -> None:
            session.systems_assumption_lock_hash = ""
            ui.notify("Lock cleared", type="info")

        with ui.row().classes("gap-2"):
            ui.button("Capture lock", on_click=_capture_lock).props("flat dense")
            ui.button("Clear lock", on_click=_clear_lock).props("flat dense")

        ui.separator().classes("q-my-sm")
        ui.label("Local sensitivities (finite difference)").classes("text-subtitle2")
        ui.label(
            "PHYS-KPI-001: Q / H98 / P_net derivatives around an INFEASIBLE base are diagnostic residue — not design claims."
        ).classes("text-caption text-orange")
        knobs = ui.select(
            ["Ip_MA", "fG", "Paux_MW", "R0_m", "Bt_T"],
            label="Knobs",
            value=["Ip_MA", "fG", "Paux_MW"],
            multiple=True,
        ).classes("w-full")
        outputs = ui.select(
            ["Q_DT_eqv", "H98", "q95_proxy", "P_e_net_MW"],
            label="Outputs",
            value=["Q_DT_eqv", "H98"],
            multiple=True,
        ).classes("w-full")
        step_h = ui.number("Step h", value=0.05, min=1e-6, step=0.01).classes("w-24")

        async def _sens() -> None:
            from ui_nicegui.lib.run_lock import (
                acquire as runlock_acquire,
                release as runlock_release,
                status as runlock_status,
                current_lease,
                lease_valid,
            )

            locked, task, is_owner = runlock_status("SystemsMode")
            if locked:
                ui.notify(
                    f"Busy: {task} — wait or force-clear from Helm."
                    if not is_owner
                    else "Systems Mode already holds the run lock.",
                    type="warning",
                )
                return
            if not runlock_acquire("Systems Mode: Local sensitivities", "SystemsMode"):
                ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
                return
            lease = current_lease()
            base, _, _ = resolve_systems_problem(session)
            k_list = list(knobs.value or [])
            o_list = list(outputs.value or [])
            h = float(step_h.value or 0.05)

            def _run():
                try:
                    from src.solvers.sensitivity import local_sensitivities
                except ImportError:
                    from solvers.sensitivity import local_sensitivities  # type: ignore
                from ui_nicegui.evaluate import ui_evaluate

                def _ev(x):
                    return ui_evaluate(x, origin="NiceGUI:SystemsSens")

                return local_sensitivities(base, params=k_list, outputs=o_list, evaluator=_ev, h=h)

            try:
                rep = await run.io_bound(_run)
                if not lease_valid(lease):
                    ui.notify("Run was force-cleared — discarding results.", type="warning")
                    return
                session.systems_sensitivities_last = rep
                ui.notify("Sensitivities computed", type="positive")
                _sens_view.refresh()
            except Exception as exc:
                ui.notify(f"Sensitivity failed: {exc}", type="negative")
            finally:
                if lease_valid(lease):
                    runlock_release("SystemsMode", lease)

        ui.button("Compute sensitivities", on_click=_sens).props("outline dense q-mb-sm")
        _sens_view(session)

        ui.separator().classes("q-my-sm")
        ui.label("QA smoke harness").classes("text-subtitle2")

        async def _qa() -> None:
            from ui_nicegui.lib.navigation import refresh_helm, refresh_status
            from ui_nicegui.lib.run_lock import (
                acquire as runlock_acquire,
                release as runlock_release,
                status as runlock_status,
                current_lease,
                lease_valid,
            )

            locked, task, is_owner = runlock_status("SystemsMode")
            if locked:
                ui.notify(
                    f"Busy: {task} — wait or force-clear from Helm."
                    if not is_owner
                    else "Systems Mode already holds the run lock.",
                    type="warning",
                )
                return
            if not runlock_acquire("Systems Mode: QA smoke", "SystemsMode"):
                ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
                return
            lease = current_lease()
            refresh_status()
            refresh_helm()

            def _run():
                try:
                    from scripts.run_systems_qa import main as qa_main
                    return int(qa_main())
                except Exception as exc:
                    return -1, str(exc)

            try:
                result = await run.io_bound(_run)
                if not lease_valid(lease):
                    ui.notify("Run was force-cleared — discarding results.", type="warning")
                    return
                if result == 0:
                    ui.notify("SYSTEMS_QA: PASS", type="positive")
                else:
                    ui.notify(f"SYSTEMS_QA: FAIL ({result})", type="negative")
            finally:
                if lease_valid(lease):
                    runlock_release("SystemsMode", lease)
                    refresh_status()
                    refresh_helm()

        ui.button("Run Systems QA smoke", on_click=_qa).props("flat dense")

        ui.separator().classes("q-my-sm")
        ui.label("Restore from artifact JSON").classes("text-subtitle2")

        async def _on_upload(e) -> None:
            try:
                raw = e.content.read() if hasattr(e.content, "read") else e.content
                obj = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
                try:
                    from src.systems.schema import upgrade_systems_artifact
                except ImportError:
                    from systems.schema import upgrade_systems_artifact  # type: ignore
                obj2 = upgrade_systems_artifact(obj)
                ui_state = obj2.get("ui_state") if isinstance(obj2.get("ui_state"), dict) else {}
                for k, v in ui_state.items():
                    if hasattr(session, k):
                        setattr(session, k, v)
                session.systems_last_solve_artifact = obj2
                ui.notify("Artifact restored to session", type="positive")
            except Exception as exc:
                ui.notify(f"Restore failed: {exc}", type="negative")

        ui.upload(on_upload=_on_upload, auto_upload=True).props("accept=.json flat dense")


@ui.refreshable
def _sens_view(session: DesignSession) -> None:
    rep = session.systems_sensitivities_last
    if not isinstance(rep, dict):
        return
    from ui_nicegui.lib.sensitivity_honesty import fd_sensitivity_table_rows
    from ui_nicegui.lib.verdict_core import verdict_summary

    art = session.systems_last_solve_artifact if isinstance(session.systems_last_solve_artifact, dict) else {}
    out = art.get("outputs") if isinstance(art.get("outputs"), dict) else {}
    if not out:
        out = session.pd_last_outputs or session.last_eval or {}
    feasible = bool(verdict_summary(out if isinstance(out, dict) else {}).get("feasible"))
    if not feasible:
        ui.label(
            "Baseline INFEASIBLE — claim-KPI sensitivities shown as diag· (PHYS-KPI-001)."
        ).classes("text-caption text-orange q-mb-xs")
    rows = fd_sensitivity_table_rows(rep, feasible=feasible, max_rows=40)
    if rows:
        ui.table(
            columns=[
                {"name": "output", "label": "Output", "field": "output"},
                {"name": "param", "label": "Param", "field": "param"},
                {"name": "sensitivity", "label": "d(out)/d(param)", "field": "sensitivity"},
            ],
            rows=rows,
            row_key="output",
        ).classes("w-full")
