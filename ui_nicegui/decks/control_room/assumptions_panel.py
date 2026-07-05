"""Control Room — assumption toggles with re-evaluation."""
from __future__ import annotations

from nicegui import run, ui

from ui_nicegui.components.empty_state import empty_state
from ui_nicegui.evaluate import ui_evaluate
from ui_nicegui.lib.cr_chronicle_helpers import point_inputs_from_artifact
from ui_nicegui.lib.cr_governance_helpers import pick_session_artifact
from ui_nicegui.session import DesignSession


def render_assumptions_panel(session: DesignSession) -> None:
    ui.label("Assumption toggles").classes("text-subtitle2")
    ui.label(
        "Fast scenario exploration — toggle common assumptions and re-evaluate the point "
        "(feasibility-first; no optimization)."
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
        return

    fuel = ui.select(["DT", "DD"], label="Fuel mode", value=str(getattr(base, "fuel_mode", "DT") or "DT"))
    ti = ui.number("Ti (keV)", value=float(getattr(base, "Ti_keV", 10.0)), step=0.5)
    paux = ui.number("Paux (MW)", value=float(getattr(base, "Paux_MW", 50.0)), step=1.0)
    tite = ui.number("Ti/Te", value=float(getattr(base, "Ti_over_Te", 2.0)), step=0.1)

    async def _apply() -> None:
        try:
            pi = session.build_point_inputs()
            pi.fuel_mode = str(fuel.value or "DT")
            pi.Ti_keV = float(ti.value or 10.0)
            pi.Paux_MW = float(paux.value or 50.0)
            pi.Ti_over_Te = float(tite.value or 2.0)
            out = await run.io_bound(ui_evaluate, pi, origin="control_room_assumptions")
            session.pd_last_outputs = out
            ui.notify("Re-evaluated with toggled assumptions", type="positive")
            _result.refresh(out)
        except Exception as exc:
            ui.notify(f"Evaluate failed: {exc}", type="negative")

    ui.button("Apply toggles and evaluate", on_click=_apply).props("color=primary outline")
    _result(session)


@ui.refreshable
def _result(session: DesignSession, out: dict | None = None) -> None:
    payload = out if isinstance(out, dict) else session.pd_last_outputs
    if not isinstance(payload, dict):
        return
    cons = payload.get("constraints") or []
    ok = all(not bool(c.get("failed")) for c in cons if isinstance(c, dict))
    ui.label(f"Feasible: {'YES' if ok else 'NO'}").classes("text-h6 " + ("text-positive" if ok else "text-negative"))
    keys = ("Q_DT_eqv", "P_fus_MW", "P_e_net_MW", "tau_E_s", "betaN", "q95")
    outs = payload.get("outputs") or payload
    for k in keys:
        if k in outs:
            ui.label(f"{k}: {outs[k]}").classes("text-caption")
