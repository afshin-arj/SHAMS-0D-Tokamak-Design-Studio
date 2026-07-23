"""Step ① — Bound feasibility precheck."""

from __future__ import annotations

import time
import math
from typing import Any, Callable, Optional

from nicegui import run, ui

from ui_nicegui.decks.systems_mode import assumption_lock_ui
from ui_nicegui.lib.helm_helpers import log_ui_event
from ui_nicegui.lib.pd_input_guardrails import notify_input_guardrails
from ui_nicegui.lib.systems_precheck import run_systems_precheck
from ui_nicegui.lib.systems_state_helpers import append_journal, resolve_systems_problem, validate_systems_problem
from ui_nicegui.session import DesignSession


def _precheck_ok(report: Any) -> bool:
    if report is None:
        return False
    try:
        return bool(getattr(report, "ok", report.get("ok", False) if isinstance(report, dict) else False))
    except Exception:
        return False


def _precheck_attr(report: Any, name: str, default=None):
    if report is None:
        return default
    v = getattr(report, name, None)
    if v is not None:
        return v
    if isinstance(report, dict):
        return report.get(name, default)
    return default


def _precheck_dominant_limiter(report: Any) -> tuple[str | None, float | None]:
    margins = _precheck_attr(report, "hard_constraints_best_margin", {}) or {}
    failed = set(_precheck_attr(report, "hard_constraints_failed_at_all_samples", []) or [])
    if not isinstance(margins, dict) or not margins:
        return None, None
    pool = [(n, m) for n, m in margins.items() if n in failed] if failed else list(margins.items())
    if not pool:
        return None, None
    name, margin = min(pool, key=lambda t: float(t[1]) if math.isfinite(float(t[1])) else -1e30)
    try:
        return str(name), float(margin)
    except (TypeError, ValueError):
        return str(name), None


def render_precheck_panel(
    session: DesignSession,
    *,
    on_precheck_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Step ① — Bound feasibility check").classes("text-subtitle1")
    ui.label(
        "Monte Carlo over declared variable bounds via frozen Evaluator. Run before target solve."
    ).classes("text-caption text-grey q-mb-sm")
    try:
        from ui_nicegui.lib.pd_solver_helpers import inputs_stale

        if inputs_stale(session):
            ui.badge("STALE", color="orange").props("outline").classes("q-mb-xs")
            ui.label(
                "Inputs changed since last Point Designer evaluation — precheck seed may not match current KPIs."
            ).classes("text-caption text-orange q-mb-xs")
    except Exception:
        pass

    assumption_lock_ui.render_assumption_lock_bar(session)

    _, targets, variables = resolve_systems_problem(session)
    valid, val_msg = validate_systems_problem(targets, variables)
    disabled = not valid
    if not valid and (targets or variables):
        ui.label(val_msg).classes("text-orange q-mb-sm")
    elif disabled:
        ui.markdown("Configure targets on tab **1 · Targets** first.").classes("text-orange")

    with ui.row().classes("gap-4 flex-wrap q-mb-sm"):
        ui.number(
            "Random samples",
            value=session.systems_precheck_n_random,
            min=1,
            max=64,
            step=1,
            on_change=lambda e: setattr(session, "systems_precheck_n_random", int(e.value or 8)),
        ).classes("w-32")
        ui.number(
            "Seed",
            value=session.systems_precheck_seed,
            min=0,
            step=1,
            on_change=lambda e: setattr(session, "systems_precheck_seed", int(e.value or 1337)),
        ).classes("w-32")

    async def _run_precheck() -> None:
        from ui_nicegui.lib.run_lock import (
            acquire as runlock_acquire,
            release as runlock_release,
            status as runlock_status,
            current_lease,
            lease_valid,
        )

        blocked, block_msg = assumption_lock_ui.assumption_lock_blocks(session)
        if blocked:
            ui.notify(block_msg, type="negative")
            return
        if session.systems_precheck_running:
            ui.notify("Precheck already running", type="warning")
            return
        locked, task, is_owner = runlock_status("SystemsMode")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Systems Mode: Precheck", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        lease = current_lease()
        t0 = time.perf_counter()
        base_now, targets_now, variables_now = resolve_systems_problem(session)
        ok_prob, prob_msg = validate_systems_problem(targets_now, variables_now)
        if not ok_prob:
            if lease_valid(lease):
                runlock_release("SystemsMode", lease)
            ui.notify(prob_msg, type="warning")
            return
        try:
            notify_input_guardrails(base_now, context="Systems Mode")
        except Exception:
            pass
        log_ui_event(
            session,
            "SystemsMode",
            "Precheck",
            {"n_random": session.systems_precheck_n_random, "seed": session.systems_precheck_seed},
        )
        session.systems_precheck_running = True
        from ui_nicegui.lib.navigation import refresh_helm, refresh_status

        refresh_status()
        refresh_helm()
        ui.notify("Running precheck…", type="info")
        try:
            report = await run.io_bound(
                run_systems_precheck,
                base_now,
                targets_now,
                variables_now,
                n_random=session.systems_precheck_n_random,
                seed=session.systems_precheck_seed,
                design_intent=session.design_intent,
                paux_for_q_mw=session.paux_for_q,
            )
            if not lease_valid(lease):
                ui.notify("Run was force-cleared — discarding results.", type="warning")
                return
            session.last_precheck_report = report
            session.systems_precheck_seconds = time.perf_counter() - t0
            append_journal(session, "Precheck", {"ok": _precheck_ok(report)})
            log_ui_event(
                session,
                "SystemsMode",
                "PrecheckResult",
                {"ok": _precheck_ok(report), "n_samples": int(_precheck_attr(report, "n_samples", 0))},
            )
            ui.notify(
                "Precheck feasible" if _precheck_ok(report) else "Precheck infeasible",
                type="positive" if _precheck_ok(report) else "warning",
            )
            _status.refresh()
        except Exception as exc:
            if lease_valid(lease):
                session.last_precheck_report = {"ok": False, "reason": "precheck_exception", "error": str(exc)}
            ui.notify(f"Precheck failed: {exc}", type="negative")
        finally:
            if lease_valid(lease):
                session.systems_precheck_running = False
                runlock_release("SystemsMode", lease)
                if on_precheck_complete:
                    on_precheck_complete()

    btn = ui.button("Run precheck", icon="play_arrow", on_click=_run_precheck).props("color=primary")
    if disabled or session.systems_precheck_running:
        btn.props("disable")

    _status(session)


@ui.refreshable
def _status(session: DesignSession) -> None:
    report = session.last_precheck_report
    if report is None:
        return
    ok = _precheck_ok(report)
    cls = "text-positive" if ok else "text-negative"
    ui.label(
        f"Status: {'✓ feasible within bounds' if ok else '✗ infeasible within bounds'} "
        f"({int(_precheck_attr(report, 'n_samples', 0))} samples)"
    ).classes(f"text-body2 q-mt-sm {cls}")

    dom, margin = _precheck_dominant_limiter(report)
    if dom:
        mtxt = f"{margin:.3g}" if margin is not None and margin == margin else "—"
        ui.label(f"Tightest hard constraint in samples: {dom} (margin {mtxt})").classes("text-caption q-mb-xs")

    failed = list(_precheck_attr(report, "hard_constraints_failed_at_all_samples", []) or [])
    with ui.expansion("Precheck details", icon="description").classes("w-full q-mt-sm"):
        if failed:
            ui.label("Failed at all samples: " + ", ".join(map(str, failed))).classes("text-orange")
        unreachable = _precheck_attr(report, "unreachable_targets", []) or []
        for u in unreachable:
            if isinstance(u, dict) and "sample_min" in u:
                ui.markdown(
                    f"- **{u.get('target')}**: requested {u.get('target_value')} "
                    f"vs range [{u.get('sample_min')}, {u.get('sample_max')}]"
                )
