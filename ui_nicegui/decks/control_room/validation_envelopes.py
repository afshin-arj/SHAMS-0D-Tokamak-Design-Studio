"""Control Room — validation envelope checks."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.lib.cr_chronicle_helpers import validation_envelope_report
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.session import DesignSession


def render_validation_envelopes(session: DesignSession) -> None:
    ui.label("Validation envelopes").classes("text-subtitle2")
    ui.markdown(
        "Decision-grade validation is **envelope-based**: check whether a solution lies within "
        "a broad reference band for key metrics, rather than matching a single reference point."
    ).classes("text-caption q-mb-sm")

    try:
        from validation.envelopes import default_envelopes

        envs = default_envelopes()
    except Exception as exc:
        ui.label(f"Validation module unavailable: {exc}").classes("text-negative")
        return

    names = list(envs.keys())
    if session.cr_validation_env not in names:
        session.cr_validation_env = names[0]
    env_sel = ui.select(
        names,
        label="Select envelope",
        value=session.cr_validation_env,
        on_change=lambda e: (
            setattr(session, "cr_validation_env", str(e.value)),
            _report.refresh(session, envs),
        ),
    ).classes("w-full q-mb-sm")
    env = envs[str(env_sel.value)]
    ui.label(env.notes).classes("text-caption q-mb-sm")

    out = session.pd_last_outputs if isinstance(session.pd_last_outputs, dict) else None
    if not out:
        empty_state("Run **Point Designer** (Evaluate) first — latest outputs are checked here.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )
        return

    _report(session, envs)


@ui.refreshable
def _report(session: DesignSession, envs: dict) -> None:
    out = session.pd_last_outputs
    if not isinstance(out, dict):
        return
    name = session.cr_validation_env
    if name not in envs:
        return

    async def _run() -> None:
        try:
            rep = await run.io_bound(validation_envelope_report, name, out)
            session.cr_validation_report = rep
            ui.notify(
                "All envelope checks passed" if rep.get("n_fail", 0) == 0 else f"{rep['n_fail']} checks failed",
                type="positive" if rep.get("n_fail", 0) == 0 else "warning",
            )
            _table.refresh()
        except Exception as exc:
            ui.notify(f"Envelope check failed: {exc}", type="negative")

    ui.button("Run envelope check", icon="fact_check", on_click=_run).props("outline")
    _table(session)


@ui.refreshable
def _table(session: DesignSession) -> None:
    rep = session.cr_validation_report
    if not isinstance(rep, dict):
        return
    rows = rep.get("rows") or []
    if not rows:
        return
    ui.table(
        columns=[
            {"name": c, "label": c, "field": c, "align": "left"}
            for c in ("metric", "value", "lo", "hi", "ok")
        ],
        rows=rows,
        row_key="metric",
    ).classes("w-full q-mt-sm")
    n_fail = int(rep.get("n_fail") or 0)
    if n_fail == 0:
        ui.label("All selected envelope checks passed.").classes("text-positive q-mt-xs")
    else:
        ui.label(
            f"{n_fail} envelope check(s) failed — targets/bounds outside the reference band (not a code error)."
        ).classes("text-warning q-mt-xs")

    ui.separator().classes("q-my-md")
    ui.label("Invariant guardrails").classes("text-subtitle2")
    ui.label("Deterministic sign/bookkeeping checks (not experimental validation).").classes("text-caption")

    async def _invariants() -> None:
        try:
            from validation.invariants import check_invariants

            rep = await run.io_bound(check_invariants, session.pd_last_outputs)
            session.cr_invariants_report = rep
            ui.notify(
                "Invariants OK" if rep.get("ok") else "Invariant failures",
                type="positive" if rep.get("ok") else "negative",
            )
            _inv.refresh()
        except Exception as exc:
            ui.notify(f"Invariants unavailable: {exc}", type="warning")

    ui.button("Run invariant guardrails", icon="rule", on_click=_invariants).props("flat outline")
    _inv(session)


@ui.refreshable
def _inv(session: DesignSession) -> None:
    rep = session.cr_invariants_report
    if not isinstance(rep, dict):
        return
    if rep.get("ok"):
        ui.label("All invariant guardrails passed.").classes("text-positive q-mt-xs")
    else:
        ui.label("Invariant guardrail failures detected.").classes("text-negative q-mt-xs")
        from ui_nicegui.components.json_view import render_json_blob

        with ui.expansion("Failure details", icon="warning").classes("w-full"):
            render_json_blob(rep.get("failures") or rep)
