"""Control Room — assumption toggles with re-evaluation."""
from __future__ import annotations

from dataclasses import asdict, replace

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.cr_chronicle_helpers import point_inputs_from_artifact
from ui_nicegui.lib.cr_governance_helpers import pick_session_artifact
from ui_nicegui.lib.navigation import switch_deck
from ui_nicegui.lib.session_store import set_point_evaluation
from ui_nicegui.lib.verdict_core import verdict_summary
from ui_nicegui.session import DesignSession


def render_assumptions_panel(session: DesignSession) -> None:
    ui.label("Assumption toggles").classes("text-subtitle2")
    ui.label(
        "Fast scenario exploration — toggle common assumptions and re-evaluate the point "
        "(feasibility-first; no optimization). Refreshes the full governance artifact."
    ).classes("text-caption q-mb-sm")

    art = pick_session_artifact(session)
    base = point_inputs_from_artifact(art) if isinstance(art, dict) else None
    if base is None:
        try:
            base = session.build_point_inputs()
        except Exception:
            base = None

    if base is None:
        empty_state("Load an artifact or run **Point Designer** to use assumption toggles.", kind="info")
        ui.button("Open Point Designer", icon="open_in_new", on_click=lambda: switch_deck("Point Designer")).props(
            "flat outline q-mt-sm"
        )
        return

    fuel = ui.select(["DT", "DD"], label="Fuel mode", value=str(getattr(base, "fuel_mode", "DT") or "DT"))
    ti = ui.number("Ti (keV)", value=float(getattr(base, "Ti_keV", 10.0)), step=0.5)
    paux = ui.number("Paux (MW)", value=float(getattr(base, "Paux_MW", 50.0)), step=1.0)
    tite = ui.number("Ti/Te", value=float(getattr(base, "Ti_over_Te", 2.0)), step=0.1)

    async def _apply() -> None:
        from ui_nicegui.lib.run_lock import acquire as runlock_acquire, release as runlock_release, status as runlock_status

        locked, task, is_owner = runlock_status("ControlRoom")
        if locked and not is_owner:
            ui.notify(f"Busy: {task} — wait or force-clear from Helm.", type="warning")
            return
        if not runlock_acquire("Control Room: Assumption toggles", "ControlRoom"):
            ui.notify("Could not acquire run lock — another evaluation is active.", type="warning")
            return
        try:
            base_pi = session.build_point_inputs()
            pi = replace(
                base_pi,
                fuel_mode=str(fuel.value or "DT"),
                Ti_keV=float(ti.value or 10.0),
                Paux_MW=float(paux.value or 50.0),
                Ti_over_Te=float(tite.value or 2.0),
            )
            out = await run.io_bound(ui_evaluate, pi, origin="control_room_assumptions")
            set_point_evaluation(session, outputs=out, inputs=asdict(pi))
            ui.notify("Re-evaluated with toggled assumptions (full artifact updated)", type="positive")
            _result.refresh(session)
            try:
                from ui_nicegui.decks.control_room.verdict import render_governance_verdict_live

                render_governance_verdict_live.refresh(session)
            except Exception:
                pass
        except Exception as exc:
            ui.notify(f"Evaluate failed: {exc}", type="negative")
        finally:
            runlock_release("ControlRoom")

    ui.button("Apply toggles and evaluate", on_click=_apply).props("color=primary outline")
    _result(session)


@ui.refreshable
def _result(session: DesignSession) -> None:
    payload = session.pd_last_outputs
    if not isinstance(payload, dict):
        return
    vs = verdict_summary(payload)
    if not vs.get("loaded"):
        return
    feasible = bool(vs.get("feasible"))
    ui.label(f"Verdict: {vs.get('verdict', 'n/a')}").classes(
        "text-h6 " + ("text-positive" if feasible else "text-negative")
    )
    ui.label(f"Dominant: {vs.get('dominant', '-')}").classes("text-body2")
    ui.label(f"{vs.get('q_label', '')} · {vs.get('nt_label', '')}").classes("text-caption")
    art = session.pd_last_artifact if isinstance(session.pd_last_artifact, dict) else {}
    kpis = art.get("kpis") if isinstance(art.get("kpis"), dict) else {}
    if kpis.get("feasible_hard") is not None:
        ui.label(f"Hard feasible (artifact KPI): {'YES' if kpis.get('feasible_hard') else 'NO'}").classes(
            "text-caption"
        )
    keys = ("Q_DT_eqv", "Pfus_total_MW", "P_e_net_MW", "tauE_eff_s", "beta_N", "q95_proxy")
    outs = payload.get("outputs") if isinstance(payload.get("outputs"), dict) else payload
    for k in keys:
        val = outs.get(k) if isinstance(outs, dict) else None
        if val is None and isinstance(outs, dict):
            # Legacy aliases for older session dumps only.
            alts = {
                "tauE_eff_s": ("tauE_s", "tau_E_s"),
                "beta_N": ("betaN_proxy", "betaN"),
                "q95_proxy": ("q95",),
            }
            for alt in alts.get(k, ()):
                if alt in outs:
                    val = outs[alt]
                    break
        if val is not None:
            ui.label(f"{k}: {val}").classes("text-caption")
