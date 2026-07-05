"""Step ① — Bound feasibility precheck."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from nicegui import run, ui

from ui_nicegui.lib.systems_precheck import run_systems_precheck
from ui_nicegui.lib.systems_state_helpers import append_journal, resolve_systems_problem
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


def render_precheck_panel(
    session: DesignSession,
    *,
    on_precheck_complete: Optional[Callable[[], None]] = None,
) -> None:
    ui.label("Step ① — Bound feasibility check").classes("text-subtitle1")
    ui.label(
        "Monte Carlo over declared variable bounds via frozen Evaluator. Run before target solve."
    ).classes("text-caption text-grey q-mb-sm")

    _, targets, variables = resolve_systems_problem(session)
    disabled = len(targets) == 0 or len(variables) == 0
    if disabled:
        ui.label("Configure targets on tab **1 · Targets** first.").classes("text-orange")

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
        if session.systems_precheck_running:
            ui.notify("Precheck already running", type="warning")
            return
        t0 = time.perf_counter()
        base_now, targets_now, variables_now = resolve_systems_problem(session)
        if not targets_now or not variables_now:
            ui.notify("Configure targets first", type="warning")
            return
        session.systems_precheck_running = True
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
            )
            session.last_precheck_report = report
            session.systems_precheck_seconds = time.perf_counter() - t0
            append_journal(session, "Precheck", {"ok": _precheck_ok(report)})
            ui.notify(
                "Precheck feasible" if _precheck_ok(report) else "Precheck infeasible",
                type="positive" if _precheck_ok(report) else "warning",
            )
            _status.refresh()
            if on_precheck_complete:
                on_precheck_complete()
        except Exception as exc:
            session.last_precheck_report = {"ok": False, "reason": "precheck_exception", "error": str(exc)}
            ui.notify(f"Precheck failed: {exc}", type="negative")
        finally:
            session.systems_precheck_running = False

    btn = ui.button("Run precheck", icon="play_arrow", on_click=_run_precheck).props("color=primary")
    if disabled:
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
