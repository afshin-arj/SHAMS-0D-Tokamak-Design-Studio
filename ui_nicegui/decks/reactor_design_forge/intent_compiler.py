"""Intent Compiler panel."""
from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.forge_helpers import (
    FORGE_RUNLOCK_OWNER,
    audit_candidate_inputs,
    candidate_to_json_bytes,
    compile_forge_candidate,
    merge_candidate_to_session_inputs,
)
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def render_intent_compiler(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Intent Compiler").classes("text-subtitle1")
    ui.label(
        "Deterministic algebraic compilation: intent → candidate PointInputs. "
        "Produces candidates only; truth remains in the evaluator."
    ).classes("text-caption text-grey q-mb-sm")

    with ui.row().classes("w-full gap-4"):
        ui.number(
            "Target fusion power P_fus (MW)",
            value=session.forge_pfus_target,
            min=0.0,
            step=10.0,
            on_change=lambda e: setattr(session, "forge_pfus_target", float(e.value or 140.0)),
        ).classes("flex-1")
        ui.number(
            "Target Q (proxy)",
            value=session.forge_q_target,
            min=0.01,
            step=0.1,
            on_change=lambda e: setattr(session, "forge_q_target", float(e.value or 2.0)),
        ).classes("flex-1")

    ui.label("Optional direct overrides (0 = ignore)").classes("text-caption q-mt-sm")
    with ui.row().classes("w-full gap-2"):
        ui.number("Override R0 (m)", value=session.forge_override_r0, step=0.1, on_change=lambda e: setattr(session, "forge_override_r0", float(e.value or 0))).classes("flex-1")
        ui.number("Override a (m)", value=session.forge_override_a, step=0.05, on_change=lambda e: setattr(session, "forge_override_a", float(e.value or 0))).classes("flex-1")
        ui.number("Override Bt (T)", value=session.forge_override_bt, step=0.5, on_change=lambda e: setattr(session, "forge_override_bt", float(e.value or 0))).classes("flex-1")
        ui.number("Override Ip (MA)", value=session.forge_override_ip, step=0.5, on_change=lambda e: setattr(session, "forge_override_ip", float(e.value or 0))).classes("flex-1")

    async def _compile() -> None:
        if session.forge_compiling:
            return
        session.forge_compiling = True
        overrides = _build_overrides(session)
        try:
            result = await run.io_bound(
                compile_forge_candidate,
                session.build_point_inputs(),
                pfus_target_mw=session.forge_pfus_target,
                q_target=session.forge_q_target,
                overrides=overrides,
            )
            session.forge_intent_compiler_last = result
            session.forge_last_audit = None
            ui.notify(f"Compiler: {result.get('status')}", type="positive" if result.get("status") == "OK" else "warning")
        except Exception as exc:
            session.last_error = str(exc)
            ui.notify(f"Compile failed: {exc}", type="negative")
        finally:
            session.forge_compiling = False
            if on_complete:
                on_complete()

    ui.button("Compile candidate", icon="build", on_click=_compile).props("color=primary outline")

    last = session.forge_intent_compiler_last
    if not isinstance(last, dict):
        return

    ui.label(f"Compiler status: {last.get('status', '?')}").classes("q-mt-sm")
    if last.get("reason"):
        ui.label(str(last.get("reason"))).classes("text-negative")

    trace = last.get("trace") or []
    if trace:
        with ui.expansion("Compilation trace", icon="list").classes("w-full"):
            for ln in trace:
                ui.markdown(f"- {ln}")

    cand = last.get("candidate_inputs")
    if isinstance(cand, dict):
        with ui.expansion("Candidate inputs", icon="data_object").classes("w-full"):
            render_json_blob(cand)
        ui.button(
            "Download candidate JSON",
            icon="download",
            on_click=lambda: ui.download(candidate_to_json_bytes(cand), "forge_candidate.json"),
        ).props("flat outline")

        async def _audit() -> None:
            if session.forge_auditing:
                return
            locked, task, is_owner = runlock_status(FORGE_RUNLOCK_OWNER)
            if locked and not is_owner:
                ui.notify(f"Run lock busy: {task or 'another task'}", type="warning")
                return
            if not runlock_acquire("Reactor Design Forge: Intent audit", FORGE_RUNLOCK_OWNER):
                ui.notify("Run lock busy (another deck is evaluating).", type="warning")
                return
            session.forge_auditing = True
            ui.notify("Auditing candidate via frozen evaluator…", type="info")
            log_ui_event(session, FORGE_RUNLOCK_OWNER, "IntentAuditStart", {})
            try:
                audit = await run.io_bound(audit_candidate_inputs, dict(cand))
                session.forge_last_audit = audit
                log_ui_event(
                    session,
                    FORGE_RUNLOCK_OWNER,
                    "IntentAuditResult",
                    {
                        "feasible": bool(audit.get("feasible")),
                        "verdict": (audit.get("verdict") or {}).get("verdict"),
                    },
                )
                ui.notify(
                    f"Audit: {audit.get('verdict', {}).get('verdict', 'done')}",
                    type="positive" if audit.get("feasible") else "warning",
                )
            except Exception as exc:
                ui.notify(f"Audit failed: {exc}", type="negative")
            finally:
                session.forge_auditing = False
                runlock_release(FORGE_RUNLOCK_OWNER)
                from ui_nicegui.lib.navigation import refresh_helm, refresh_status

                refresh_status()
                refresh_helm()
                if on_complete:
                    on_complete()

        ui.button("Audit candidate (frozen evaluator)", icon="verified", on_click=_audit).props("outline")

        def _apply() -> None:
            from ui_nicegui.lib.session_store import clear_point_designer

            clear_point_designer(session)
            session.inputs = merge_candidate_to_session_inputs(session.inputs, cand)
            from ui_nicegui.lib.pd_handoff import navigate_to_point_designer

            navigate_to_point_designer(session)
            ui.notify(
                "Opened Point Designer with Forge candidate — Evaluate Point to refresh KPIs.",
                type="positive",
            )

        ui.button("Apply in Point Designer", icon="upload", on_click=_apply).props("outline flat")

    if isinstance(session.forge_last_audit, dict):
        _render_audit_detail(session.forge_last_audit)


def _build_overrides(session: DesignSession) -> dict:
    overrides = {}
    if session.forge_override_r0 > 0:
        overrides["R0_m"] = float(session.forge_override_r0)
    if session.forge_override_a > 0:
        overrides["a_m"] = float(session.forge_override_a)
    if session.forge_override_bt > 0:
        overrides["Bt_T"] = float(session.forge_override_bt)
    if session.forge_override_ip > 0:
        overrides["Ip_MA"] = float(session.forge_override_ip)
    return overrides


def _render_audit_detail(audit: dict) -> None:
    with ui.expansion("Audit detail (constraint ledger excerpt)", icon="gavel").classes("w-full q-mt-sm"):
        rows = audit.get("constraint_rows") or []
        if rows:
            ui.table(
                columns=[
                    {"name": "name", "label": "Constraint", "field": "name", "align": "left"},
                    {"name": "passed", "label": "Pass", "field": "passed"},
                    {"name": "value", "label": "Value", "field": "value"},
                    {"name": "limit", "label": "Limit", "field": "limit"},
                ],
                rows=[{k: r.get(k) for k in ("name", "passed", "value", "limit")} for r in rows[:15]],
                row_key="name",
            ).classes("w-full")
