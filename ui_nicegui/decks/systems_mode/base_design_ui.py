"""Starting machine baseline for Systems workflow."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.systems_state_helpers import merge_base_overrides_into_session
from ui_nicegui.session import DesignSession


def render_base_design_editor(session: DesignSession) -> None:
    ui.label("Starting machine (Systems baseline)").classes("text-subtitle1")
    ui.label(
        "Optional overrides for precheck/solve/recovery. Does not change frozen evaluator — only the starting PointInputs."
    ).classes("text-caption q-mb-sm")

    bo = dict(session.systems_base_overrides or {})
    inp = session.inputs or {}

    def _val(key: str, default: float) -> float:
        if key in bo:
            return float(bo[key])
        try:
            return float(inp.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    defaults = {
        "R0_m": 1.81, "a_m": 0.62, "kappa": 1.8, "delta": 0.0,
        "Bt_T": 10.0, "Ti_keV": 10.0, "Ti_over_Te": 1.0, "t_shield_m": 0.8,
    }
    fields = {}
    for key, label, step in (
        ("R0_m", "R₀ [m]", 0.01),
        ("a_m", "a [m]", 0.01),
        ("kappa", "κ [-]", 0.01),
        ("delta", "δ [-]", 0.02),
        ("Bt_T", "B_t [T]", 0.1),
        ("Ti_keV", "T_i [keV]", 0.5),
        ("Ti_over_Te", "T_i/T_e [-]", 0.05),
        ("t_shield_m", "Shield [m]", 0.01),
    ):
        fields[key] = ui.number(
            label, value=_val(key, defaults[key]), min=0.0, step=step,
        ).classes("w-full q-mb-xs")

    def _capture() -> None:
        overrides = {k: float(w.value or 0) for k, w in fields.items()}
        session.systems_base_overrides = overrides
        merge_base_overrides_into_session(session, overrides)
        ui.notify("Starting machine updated", type="positive")

    def _undo_base() -> None:
        hist = list(session.systems_base_history or [])
        if not hist:
            ui.notify("No history", type="warning")
            return
        last = hist.pop()
        prev = dict(last.get("base_overrides") or {})
        session.systems_base_history = hist
        session.systems_base_overrides = prev
        for k, v in prev.items():
            if k in session.inputs:
                session.inputs[k] = float(v)
        ui.notify("Undid last base change", type="info")

    ui.button("Apply to session", icon="save", on_click=_capture).props("outline q-mt-sm")
    ui.button("Undo", icon="undo", on_click=_undo_base).props("flat q-ml-sm")
