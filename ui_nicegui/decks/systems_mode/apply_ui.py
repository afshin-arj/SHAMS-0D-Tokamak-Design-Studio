"""Promote candidate to Point Designer."""

from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.pd_artifact_helpers import build_point_artifact
from ui_nicegui.lib.compare_helpers import build_compare_artifact, open_compare_deck, store_compare_slot
from ui_nicegui.lib.pd_handoff import navigate_to_point_designer
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.lib.systems_ranking_helpers import rank_candidates
from ui_nicegui.lib.systems_workflow_helpers import apply_x_to_session, collect_candidates
from ui_nicegui.session import DesignSession
from ui_nicegui.components.json_view import render_json_blob


def _push_apply_undo(session: DesignSession) -> None:
    stack = list(getattr(session, "systems_apply_undo_stack", []) or [])
    stack.append({"inputs": dict(session.inputs or {})})
    session.systems_apply_undo_stack = stack[-8:]


def _pop_apply_undo(session: DesignSession) -> bool:
    stack = list(getattr(session, "systems_apply_undo_stack", []) or [])
    if not stack:
        return False
    snap = stack.pop()
    session.systems_apply_undo_stack = stack
    for k, v in (snap.get("inputs") or {}).items():
        if k in session.inputs:
            session.inputs[k] = float(v)
    return True


def render_apply_panel(session: DesignSession, *, on_complete=None) -> None:
    ui.label("Promote candidate to Point Designer").classes("text-subtitle1")
    ui.label(
        "Applies iteration variables to PD inputs, then re-evaluates through the frozen Evaluator choke point."
    ).classes("text-caption q-mb-sm")

    cands = rank_candidates(collect_candidates(session), session.systems_ranking_profile)
    if not cands:
        ui.label("No candidates — run target solve, recovery, or search first.").classes("text-grey")

        def _goto_targets() -> None:
            session.systems_workflow_step = "1 · Targets"
            if on_complete:
                on_complete()

        def _goto_solve() -> None:
            session.systems_workflow_step = "2 · Check & Solve"
            if on_complete:
                on_complete()

        with ui.row().classes("gap-2 q-mt-sm flex-wrap"):
            ui.button("Set targets", icon="flag", on_click=_goto_targets).props("outline")
            ui.button("Run precheck / solve", icon="play_arrow", on_click=_goto_solve).props(
                "outline color=primary"
            )
        return

    labels = []
    for i, c in enumerate(cands):
        h = c.get("headline") or {}
        feas = bool(c.get("feasible"))
        mark = "✓" if feas else "✗"
        q_disp = h.get("Q", "-") if feas else "— (diag)"
        labels.append(
            f"#{i + 1} {c['source']} | Q={q_disp} | feasible={mark}"
        )
    ids = [c["id"] for c in cands]
    if session.systems_selected_candidate_id not in ids:
        session.systems_selected_candidate_id = next(
            (c["id"] for c in cands if bool(c.get("feasible"))),
            cands[0]["id"],
        )

    ui.select(
        labels,
        label="Candidate (ranked)",
        value=labels[ids.index(session.systems_selected_candidate_id)],
        on_change=lambda e: _pick(session, cands, labels, str(e.value)),
    ).classes("w-full q-mb-sm")

    sel = _selected(cands, session.systems_selected_candidate_id)
    if sel and not bool(sel.get("feasible")):
        ui.label(
            "PHYS-KPI-001: selected candidate is INFEASIBLE — Q/H98/Pfus in headlines are diagnostic residue; "
            "Apply re-evaluates under frozen truth and may remain NO-SOLUTION."
        ).classes("text-caption text-orange q-mb-sm")
    if sel and isinstance(sel.get("x"), dict) and session.systems_expert_view:
        with ui.expansion("Candidate variables (expert)"):
            render_json_blob(sel["x"])

    async def _apply_evaluate() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        sel_now = _selected(cands, session.systems_selected_candidate_id)
        if not sel_now or not isinstance(sel_now.get("x"), dict):
            ui.notify("No candidate selected", type="warning")
            return
        if not bool(sel_now.get("feasible")):
            ui.notify(
                "Applying INFEASIBLE candidate — KPIs are diagnostic until a feasible re-evaluate.",
                type="warning",
            )
        locked, task, is_owner = runlock_status("SystemsMode")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Systems Mode: Apply → Point Designer", "SystemsMode"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        _push_apply_undo(session)
        applied = apply_x_to_session(session, sel_now["x"])
        ui.notify(f"Applied {len(applied)} variables", type="info")
        try:
            inp = session.build_point_inputs()
            out = await run.io_bound(
                ui_evaluate,
                inp,
                origin="NiceGUI:SystemsApply",
                Paux_for_Q_MW=session.paux_for_q,
            )
            inputs_dict = inp.to_dict() if hasattr(inp, "to_dict") else dict(session.inputs)
            set_point_evaluation(session, outputs=out, inputs=inputs_dict)
            applied_art = build_point_artifact(
                inputs=inputs_dict,
                outputs=out,
                design_intent=session.design_intent,
            )
            # Apply is a PD re-eval, not a Systems target solve (provenance honesty).
            applied_art["source"] = "point_designer_apply"
            session.systems_last_solve_artifact = applied_art
            from ui_nicegui.lib.verdict_core import verdict_summary

            vs = verdict_summary(out if isinstance(out, dict) else {})
            if vs.get("feasible"):
                ui.notify("Re-evaluated via Point Designer — FEASIBLE.", type="positive")
            else:
                ui.notify(
                    "Re-evaluated via Point Designer — INFEASIBLE (diagnostic KPIs only; not a design claim).",
                    type="warning",
                )
            if on_complete:
                on_complete()
        except Exception as exc:
            _pop_apply_undo(session)
            ui.notify(f"Apply failed: {exc}", type="negative")
        finally:
            runlock_release("SystemsMode")

    def _undo_apply() -> None:
        if _pop_apply_undo(session):
            try:
                from ui_nicegui.lib.navigation import refresh_helm, refresh_status

                refresh_helm()
                refresh_status()
            except Exception:
                pass
            ui.notify("Undid last apply — Point Designer inputs restored (KPIs STALE).", type="warning")
            if on_complete:
                on_complete()
        else:
            ui.notify("Nothing to undo", type="warning")

    async def _send_compare(slot: str) -> None:
        sel_now = _selected(cands, session.systems_selected_candidate_id)
        if not sel_now or not isinstance(sel_now.get("x"), dict):
            return
        # build_compare_artifact snapshots/restores session.inputs — no silent PD mutation
        patch = dict(sel_now["x"])
        label = f"Systems ({sel_now.get('source')})"
        art = await run.io_bound(lambda: build_compare_artifact(session, patch, label=label))
        store_compare_slot(session, art, slot, label=label)
        ui.notify(f"Sent to Compare slot {slot}", type="positive")

    def _open_pd() -> None:
        navigate_to_point_designer(session)
        ui.notify("Opened Point Designer Configure.", type="info")

    apply_props = "color=primary w-full q-mb-sm"
    if sel and bool(sel.get("feasible")):
        ui.button(
            "Apply to PD & re-evaluate",
            icon="check",
            on_click=_apply_evaluate,
        ).props(apply_props)
    else:
        ui.label(
            "No feasible candidate selected — primary promote is gated; diagnostic Apply remains available."
        ).classes("text-caption text-orange q-mb-xs")
        ui.button(
            "Apply diagnostic seed to PD & re-evaluate",
            icon="warning",
            on_click=_apply_evaluate,
        ).props("outline color=orange w-full q-mb-sm")
    ui.button("Undo last apply", icon="undo", on_click=_undo_apply).props("flat q-mb-sm")
    with ui.row().classes("gap-2 flex-wrap"):
        ui.button("Open Point Designer", icon="design_services", on_click=_open_pd).props("outline color=primary")
        ui.button("Compare slot A", on_click=lambda: _send_compare("A")).props("outline")
        ui.button("Compare slot B", on_click=lambda: _send_compare("B")).props("outline")
        ui.button("Open Compare deck", icon="compare_arrows", on_click=lambda: open_compare_deck(session)).props(
            "flat outline"
        )


def _pick(session: DesignSession, cands: list, labels: list, label: str) -> None:
    try:
        session.systems_selected_candidate_id = cands[labels.index(label)]["id"]
    except ValueError:
        pass


def _selected(cands: list, cid: str) -> dict | None:
    for c in cands:
        if c.get("id") == cid:
            return c
    return cands[0] if cands else None
