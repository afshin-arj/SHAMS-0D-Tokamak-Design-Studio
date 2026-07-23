"""Step ② — Newton target solve."""

from __future__ import annotations

from typing import Callable, Optional

from nicegui import run, ui

from ui_nicegui.decks.systems_mode import assumption_lock_ui
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pd_input_guardrails import notify_input_guardrails
from ui_nicegui.lib.systems_solve_helpers import run_systems_solve
from ui_nicegui.lib.systems_state_helpers import append_journal, resolve_systems_problem, validate_systems_problem
from ui_nicegui.lib.systems_target_banner import systems_target_rows
from ui_nicegui.lib.systems_workflow_helpers import append_run_card, systems_run_payload
from ui_nicegui.session import DesignSession


def _render_solver_numerics(session: DesignSession) -> None:
    with ui.row().classes("gap-4 flex-wrap"):
        ui.number(
            "Max iterations",
            value=session.systems_max_iter,
            min=5,
            max=200,
            step=1,
            on_change=lambda e: setattr(session, "systems_max_iter", int(e.value or 35)),
        ).classes("w-32")
        ui.number(
            "Tolerance",
            value=session.systems_tol,
            min=1e-6,
            max=1e-1,
            step=1e-4,
            format="%.1e",
            on_change=lambda e: setattr(session, "systems_tol", float(e.value or 1e-3)),
        ).classes("w-32")
        ui.number(
            "Damping",
            value=session.systems_damping,
            min=0.05,
            max=1.0,
            step=0.05,
            on_change=lambda e: setattr(session, "systems_damping", float(e.value or 0.6)),
        ).classes("w-32")
    ui.checkbox(
        "Block-ordered solve",
        value=session.systems_block_solve,
        on_change=lambda e: setattr(session, "systems_block_solve", bool(e.value)),
    )
    ui.checkbox(
        "Continuation ramp",
        value=session.systems_do_continuation,
        on_change=lambda e: setattr(session, "systems_do_continuation", bool(e.value)),
    )
    ui.number(
        "Continuation steps",
        value=session.systems_cont_steps,
        min=2,
        max=30,
        on_change=lambda e: setattr(session, "systems_cont_steps", int(e.value or 10)),
    ).classes("w-32")
    ui.checkbox(
        "Feasibility scout",
        value=session.systems_feasibility_scout_enabled,
        on_change=lambda e: setattr(session, "systems_feasibility_scout_enabled", bool(e.value)),
    )
    ui.checkbox(
        "Require passing precheck (reactor)",
        value=session.systems_do_precheck,
        on_change=lambda e: setattr(session, "systems_do_precheck", bool(e.value)),
    )


def render_solve_panel(
    session: DesignSession,
    *,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Step ② — Target solve (Newton)").classes("text-subtitle1")
    ui.label("Adjust declared variables to hit targets. Uses frozen Evaluator.").classes("text-caption q-mb-sm")

    assumption_lock_ui.render_assumption_lock_bar(session)

    _, targets, variables = resolve_systems_problem(session)
    valid, val_msg = validate_systems_problem(targets, variables)
    disabled = not valid
    if not valid and (targets or variables):
        ui.label(val_msg).classes("text-caption text-orange q-mb-sm")
    elif disabled:
        ui.markdown("Complete tab **1 · Targets** first.").classes("text-orange")

    pre = session.last_precheck_report
    if pre is not None:
        ok = bool(getattr(pre, "ok", pre.get("ok") if isinstance(pre, dict) else False))
        ui.label(f"Precheck: {'✓ pass' if ok else '✗ fail'}").classes("text-caption q-mb-sm")

    if session.systems_expert_view:
        with ui.expansion("Solver numerics", icon="settings").classes("w-full q-mb-sm"):
            _render_solver_numerics(session)

    async def _run_solve() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        blocked, block_msg = assumption_lock_ui.assumption_lock_blocks(session)
        if blocked:
            ui.notify(block_msg, type="negative")
            return
        if getattr(session, "systems_solve_running", False):
            ui.notify("Target solve already running", type="warning")
            return
        base_now, targets_now, variables_now = resolve_systems_problem(session)
        ok_prob, prob_msg = validate_systems_problem(targets_now, variables_now)
        if not ok_prob:
            ui.notify(prob_msg, type="warning")
            return
        locked, task, is_owner = runlock_status("SystemsMode")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Systems Mode: Target solve", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        from ui_nicegui.lib.run_lock import current_lease, lease_valid

        lease = current_lease()
        session.systems_solve_running = True
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        # HELM-BUSY-001: acquire paints chrome; re-paint after session flag for orphan labels.
        refresh_status()
        refresh_helm()
        try:
            try:
                notify_input_guardrails(base_now, context="Systems Mode")
            except Exception:
                pass
            log_ui_event(
                session,
                "SystemsMode",
                "TargetSolve",
                {"targets": dict(targets_now), "variables": list(variables_now.keys())},
            )
            ui.notify("Running target solve…", type="info")
            trust = float(session.systems_trust_delta) if session.systems_use_trust_delta else None
            result = await run.io_bound(
                run_systems_solve,
                base_now,
                targets_now,
                variables_now,
                max_iter=session.systems_max_iter,
                tol=session.systems_tol,
                damping=session.systems_damping,
                block_solve=session.systems_block_solve,
                design_intent=session.design_intent,
                trust_delta=trust,
                do_continuation=session.systems_do_continuation,
                cont_steps=session.systems_cont_steps,
                scout_enabled=session.systems_feasibility_scout_enabled,
                scout_n_samples=session.systems_scout_n_samples,
                scout_n_refine=session.systems_scout_n_refine,
                scout_seed=session.systems_precheck_seed,
                input_overrides=dict(session.systems_inputs_overrides or {}),
                precheck_report=session.last_precheck_report,
                require_precheck=session.systems_do_precheck,
                paux_for_q_mw=session.paux_for_q,
            )
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding solve results.", type="warning")
                return
            if result.get("blocked"):
                ui.notify(str(result.get("message", "Solve blocked")), type="warning")
                return
            session.systems_last_solve_result = result
            session.systems_last_solve_artifact = result.get("artifact")
            # Propose-only: never overwrite Point Designer via set_point_evaluation here.
            # Promote exclusively through tab 4 · Apply (re-eval + runlock + undo).
            append_run_card(
                session,
                kind="SystemsSolve",
                settings={"targets": dict(targets_now), "variables": list(variables_now.keys())},
                outcome={"ok": bool(result.get("ok")), "iters": result.get("iters")},
                payload=systems_run_payload(session, result.get("artifact")),
            )
            append_journal(session, "SystemsSolve", {"ok": bool(result.get("ok"))})
            log_ui_event(
                session,
                "SystemsMode",
                "TargetSolveResult",
                {
                    "ok": bool(result.get("ok")),
                    "iters": result.get("iters"),
                    "blocked": bool(result.get("blocked")),
                },
            )
            converged = bool(result.get("target_converged", result.get("ok")))
            feasible = bool(result.get("intent_feasible", result.get("ok")))
            blocking = result.get("blocking_failed") or []
            if converged and not feasible:
                ui.notify(
                    f"Target floors met (≥) but intent-blocking constraints failed: {', '.join(blocking[:3])}",
                    type="warning",
                )
            elif converged and feasible:
                ui.notify(
                    f"Target floors met (≥) and intent-feasible ({result.get('iters')} iter) — "
                    "use 4 · Apply to promote into Point Designer.",
                    type="positive",
                )
            else:
                ui.notify(
                    f"{'Finished without meeting target floors (≥)' if not converged else 'Floors met, not intent-feasible'} "
                    f"({result.get('iters')} iter) — Point Designer baseline unchanged; use 4 · Apply to promote.",
                    type="warning",
                )
            _solve_result.refresh()
        except Exception as exc:
            ui.notify(f"Target solve failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                session.systems_solve_running = False
                runlock_release("SystemsMode", lease)
                if on_complete:
                    on_complete()

    btn = ui.button("Run target solve", icon="bolt", on_click=_run_solve).props("color=primary q-mt-sm")
    if disabled or session.systems_solve_running:
        btn.props("disable")
    _solve_result(session)


@ui.refreshable
def _solve_result(session: DesignSession) -> None:
    result = session.systems_last_solve_result
    if not isinstance(result, dict):
        return
    converged = bool(result.get("target_converged", result.get("ok")))
    feasible = bool(result.get("intent_feasible", result.get("ok")))
    ui.label(
        f"Last solve: target_floors_met(≥)={converged} | intent_feasible={feasible} | "
        f"iters={result.get('iters', '-')} | {float(result.get('wall_s', 0)):.2f}s"
    ).classes("text-body2 q-mt-sm")
    blocking = result.get("blocking_failed") or []
    if blocking:
        ui.label(f"Blocking constraints: {', '.join(map(str, blocking[:5]))}").classes("text-caption text-orange")
    out = result.get("out")
    if isinstance(out, dict) and out:
        tgt_rows = systems_target_rows(session, out, feasible=feasible)
        if tgt_rows:
            if not feasible:
                ui.label(
                    "PHYS-KPI-001: target table values are evaluated/diagnostic when intent-infeasible — not design achievements. "
                    "Status ``diag`` means the floor was met numerically but the point remains INFEASIBLE."
                ).classes("text-caption text-orange q-mb-xs")
            ui.table(
                columns=[
                    {"name": "quantity", "label": "Quantity", "field": "quantity", "align": "left"},
                    {"name": "target", "label": "Target", "field": "target"},
                    {
                        "name": "achieved",
                        "label": "Evaluated" if not feasible else "Achieved",
                        "field": "achieved",
                    },
                    {"name": "status", "label": "Status", "field": "status"},
                ],
                rows=tgt_rows,
                row_key="quantity",
            ).classes("w-full q-mt-sm")
