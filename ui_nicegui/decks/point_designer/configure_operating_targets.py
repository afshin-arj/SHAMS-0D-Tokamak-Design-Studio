"""Operating targets & solver controls for Point Designer Configure."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.lib.pd_solver_helpers import sync_solver_bounds_from_inputs
from ui_nicegui.session import DesignSession

_EVAL_MODE_LABELS = {
    "direct": "Direct evaluate (fixed Ip, fG)",
    "solver": "Nested match H98(y,2) + Q_DT_eqv",
    "envelope": "Coupled envelope (Ip, fG[/Paux])",
}
_EVAL_MODE_VALUES = list(_EVAL_MODE_LABELS.keys())


def render_operating_targets(session: DesignSession, *, embedded: bool = False) -> None:
    sync_solver_bounds_from_inputs(session)
    inp = session.inputs
    mode = str(session.pd_eval_mode)

    def _body() -> None:
        fuel_label = (
            "DT performance (targets Q & net electric)"
            if str(inp.get("fuel_mode", "DT")) == "DT"
            else "DD feasibility (secondary DT from DD-produced T)"
        )
        ui.select(
            list(_EVAL_MODE_LABELS.values()),
            label="Evaluation mode",
            value=_EVAL_MODE_LABELS.get(mode, _EVAL_MODE_LABELS["direct"]),
            on_change=lambda e: setattr(
                session,
                "pd_eval_mode",
                _EVAL_MODE_VALUES[
                    list(_EVAL_MODE_LABELS.values()).index(str(e.value))
                ],
            ),
        ).classes("w-full")
        ui.label(
            "Direct — evaluate at Configure Ip/fG. Nested — outer Ip adjusts H98(y,2), "
            "inner fG adjusts Q_DT_eqv. Envelope — coupled Newton on Ip/fG (and Paux if power target set). "
            "Not the v396 transport-envelope authority overlay."
        ).classes("text-caption")

        ui.select(
            ["DT performance (targets Q & net electric)", "DD feasibility (secondary DT from DD-produced T)"],
            label="Fuel / design mode",
            value=fuel_label,
            on_change=lambda e: inp.__setitem__(
                "fuel_mode", "DT" if str(e.value).startswith("DT") else "DD"
            ),
        ).classes("w-full")

        if str(inp.get("fuel_mode", "DT")) == "DD":
            ui.label(
                "DD mode caps Q target ≤ 0.05 and H98 target ≤ 1.0 when switching fuel."
            ).classes("text-caption text-info")
            ui.checkbox(
                "Include secondary DT from DD-produced tritium",
                value=bool(session.pd_include_secondary_dt),
                on_change=lambda e: setattr(session, "pd_include_secondary_dt", bool(e.value)),
            )
            if session.pd_include_secondary_dt:
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.number(
                        "Tritium retention f_ret",
                        value=session.pd_tritium_retention,
                        min=0.0, max=1.0, step=0.05,
                        on_change=lambda e: setattr(session, "pd_tritium_retention", e.value),
                    )
                    ui.number(
                        "Tritium loss time tau_T (s)",
                        value=session.pd_tau_t_loss_s,
                        min=0.1, step=0.5,
                        on_change=lambda e: setattr(session, "pd_tau_t_loss_s", e.value),
                    )

        if mode != "direct":
            fuel = str(inp.get("fuel_mode", "DT"))
            q_def = 2.0 if fuel == "DT" else 0.05
            h_def = 1.15 if fuel == "DT" else 1.0
            paux_q = float(inp.get("Paux_for_Q_MW", inp.get("Paux_MW", 50.0)))
            paux = float(inp.get("Paux_MW", 50.0))
            if paux_q != paux:
                ui.label(
                    f"Q_DT_eqv uses Paux_for_Q ({paux_q:.2g} MW), not heating Paux ({paux:.2g} MW)."
                ).classes("text-caption text-orange")

            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Target Q_DT_eqv",
                    value=session.pd_q_target or q_def,
                    min=0.0, step=0.05,
                    on_change=lambda e: setattr(session, "pd_q_target", e.value),
                )
                ui.number(
                    "Target H98(y,2)",
                    value=session.pd_h98_target or h_def,
                    min=0.1, step=0.05,
                    on_change=lambda e: setattr(session, "pd_h98_target", e.value),
                )
                ui.number(
                    "Ip min (MA)",
                    value=session.pd_ip_min,
                    min=0.1, step=0.1,
                    on_change=lambda e: setattr(session, "pd_ip_min", e.value),
                )
                ui.number(
                    "Ip max (MA)",
                    value=session.pd_ip_max,
                    min=0.1, step=0.1,
                    on_change=lambda e: setattr(session, "pd_ip_max", e.value),
                )
                ui.number(
                    "fG min",
                    value=session.pd_fg_min,
                    min=0.0, max=2.0, step=0.01,
                    on_change=lambda e: setattr(session, "pd_fg_min", e.value),
                )
                ui.number(
                    "fG max",
                    value=session.pd_fg_max,
                    min=0.0, max=2.0, step=0.01,
                    on_change=lambda e: setattr(session, "pd_fg_max", e.value),
                )
                ui.number(
                    "Solver tolerance",
                    value=session.pd_solver_tol,
                    min=1e-6, max=0.1, step=1e-4,
                    on_change=lambda e: setattr(session, "pd_solver_tol", e.value),
                )

            ui.checkbox(
                "Record solver trace (Chronicle export)",
                value=bool(session.pd_show_solver_live),
                on_change=lambda e: setattr(session, "pd_show_solver_live", bool(e.value)),
            )

            if mode == "envelope":
                ui.label(
                    "Optional power targets — leave at 0 to ignore. "
                    "When set, Paux is added as a solve variable (must match target count)."
                ).classes("text-caption q-mt-sm")
                with ui.grid(columns=2).classes("w-full gap-2"):
                    ui.number(
                        "Target Pfus_DT_adj (MW); 0 = ignore",
                        value=session.pd_pfus_target,
                        min=0.0, step=10.0,
                        on_change=lambda e: setattr(session, "pd_pfus_target", e.value),
                    )
                    ui.number(
                        "Target P_e_net (MW); ≤0 = ignore",
                        value=session.pd_pnet_target,
                        step=10.0,
                        on_change=lambda e: setattr(session, "pd_pnet_target", e.value),
                    )
        else:
            ui.label(
                "Direct mode evaluates at plasma-state Ip and fG — solver targets and bounds are hidden."
            ).classes("text-caption")

        if session.pd_expert_view:
            with ui.expansion(
                "Experimental input search (expert only)",
                icon="science",
            ).classes("w-full q-mt-sm"):
                ui.label(
                    "Random-search input proposals before evaluate — SHAMS re-evaluates every "
                    "candidate with frozen physics. Not L0 optimization."
                ).classes("text-caption q-mb-sm")
                if session.pd_do_opt and mode in ("solver", "envelope"):
                    ui.label(
                        "Search runs first; solver then re-targets H98/Q on the proposed point."
                    ).classes("text-caption text-orange q-mb-sm")
                ui.checkbox(
                    "Run constrained search before evaluate",
                    value=bool(session.pd_do_opt),
                    on_change=lambda e: setattr(session, "pd_do_opt", bool(e.value)),
                )
                if session.pd_do_opt:
                    with ui.grid(columns=3).classes("w-full gap-2"):
                        ui.select(
                            ["min_R0", "min_Bpeak", "max_Pnet", "min_recirc"],
                            label="Objective",
                            value=session.pd_opt_objective,
                            on_change=lambda e: setattr(session, "pd_opt_objective", str(e.value)),
                        )
                        ui.number(
                            "Iterations",
                            value=session.pd_opt_iters,
                            min=20,
                            step=10,
                            on_change=lambda e: setattr(
                                session, "pd_opt_iters", int(e.value or 200)
                            ),
                        )
                        ui.number(
                            "Seed",
                            value=session.pd_opt_seed,
                            min=0,
                            step=1,
                            on_change=lambda e: setattr(session, "pd_opt_seed", int(e.value or 1)),
                        )

    if embedded:
        _body()
        return

    with ui.expansion("Operating targets & solver", icon="gps_fixed").classes("w-full"):
        _body()
