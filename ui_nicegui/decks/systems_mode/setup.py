"""Systems Mode setup — target specification."""

from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.systems_state_helpers import resolve_systems_problem
from ui_nicegui.session import DesignSession


def _render_baseline_summary(session: DesignSession) -> None:
    inp = session.inputs or {}
    ui.label("Starting point (Point Designer — edit under Starting machine →)").classes("text-caption q-mb-xs")
    with ui.row().classes("gap-3 flex-wrap q-mb-sm"):
        for key, label in (
            ("R0_m", "R₀ [m]"),
            ("B_T", "B_t [T]"),
            ("Ip_MA", "I_p [MA]"),
            ("Paux_MW", "P_aux [MW]"),
            ("fG", "f_G [-]"),
        ):
            val = inp.get(key, "-")
            with ui.card().classes("p-2"):
                ui.label(label).classes("text-caption text-grey")
                ui.label(str(val)).classes("text-body2")


def render_setup(session: DesignSession) -> None:
    ui.label("Target specification").classes("text-subtitle1")
    ui.label(
        "Left: performance targets the solver must hit. Right: which plasma/plant knobs it may adjust within bounds."
    ).classes("text-caption text-grey q-mb-sm")

    _render_baseline_summary(session)
    _, targets, variables = resolve_systems_problem(session)

    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            ui.label("What should the point achieve?").classes("text-subtitle2")
            ui.checkbox(
                "Match fusion gain Q",
                value=session.systems_use_q,
                on_change=lambda e: setattr(session, "systems_use_q", bool(e.value)),
            )
            ui.number(
                "Q target [-]",
                value=session.systems_q_target,
                min=0.5,
                step=0.5,
                on_change=lambda e: setattr(session, "systems_q_target", float(e.value or 10.0)),
            ).classes("w-full")
            ui.checkbox(
                "Match confinement H98",
                value=session.systems_use_h,
                on_change=lambda e: setattr(session, "systems_use_h", bool(e.value)),
            )
            ui.number(
                "H98 target [-]",
                value=session.systems_h_target,
                min=0.05,
                step=0.05,
                on_change=lambda e: setattr(session, "systems_h_target", float(e.value or 1.15)),
            ).classes("w-full")
            ui.checkbox(
                "Match net electric P_net",
                value=session.systems_use_pnet,
                on_change=lambda e: setattr(session, "systems_use_pnet", bool(e.value)),
            )
            ui.number(
                "P_net target [MW(e)]",
                value=session.systems_pnet_target,
                min=5.0,
                step=5.0,
                on_change=lambda e: setattr(session, "systems_pnet_target", float(e.value or 50.0)),
            ).classes("w-full")
        with ui.column().classes("flex-1"):
            ui.label("What may the solver adjust?").classes("text-subtitle2")
            ui.checkbox(
                "Plasma current I_p [MA]",
                value=session.systems_solve_ip,
                on_change=lambda e: setattr(session, "systems_solve_ip", bool(e.value)),
            )
            ui.checkbox(
                "Greenwald fraction f_G [-]",
                value=session.systems_solve_fg,
                on_change=lambda e: setattr(session, "systems_solve_fg", bool(e.value)),
            )
            ui.checkbox(
                "Auxiliary power P_aux [MW]",
                value=session.systems_solve_paux,
                on_change=lambda e: setattr(session, "systems_solve_paux", bool(e.value)),
            )

    if targets and variables:
        ui.label(
            f"Ready: targets={', '.join(targets.keys())} | adjustable={', '.join(variables.keys())}"
        ).classes("text-caption text-positive q-mt-sm")
    else:
        ui.label("Enable at least one target and one adjustable variable.").classes("text-orange q-mt-sm")
