"""Operating targets & solver controls for Point Designer Configure."""

from __future__ import annotations



from nicegui import ui



from ui_nicegui.lib.pd_solver_helpers import sync_solver_bounds_from_inputs

from ui_nicegui.session import DesignSession





def render_operating_targets(session: DesignSession, *, embedded: bool = False) -> None:

    sync_solver_bounds_from_inputs(session)

    inp = session.inputs



    def _body() -> None:

        ui.select(

            ["DT performance (targets Q & net electric)", "DD feasibility (secondary DT from DD-produced T)"],

            label="Fuel / design mode",

            value="DT performance (targets Q & net electric)"

            if str(inp.get("fuel_mode", "DT")) == "DT"

            else "DD feasibility (secondary DT from DD-produced T)",

            on_change=lambda e: inp.__setitem__(

                "fuel_mode", "DT" if str(e.value).startswith("DT") else "DD"

            ),

        ).classes("w-full")



        if str(inp.get("fuel_mode", "DT")) == "DD":

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



        ui.select(

            ["direct", "solver", "envelope"],

            label="Evaluation mode",

            value=session.pd_eval_mode,

            on_change=lambda e: setattr(session, "pd_eval_mode", str(e.value)),

        ).classes("w-full")

        ui.label(

            "direct — evaluate at Configure Ip/fG; solver — nested Ip+fG for target H98/Q; "

            "envelope — bounded vector solve (SPARC-like)."

        ).classes("text-caption")



        fuel = str(inp.get("fuel_mode", "DT"))

        q_def = 2.0 if fuel == "DT" else 0.05

        h_def = 1.15 if fuel == "DT" else 1.0



        with ui.grid(columns=2).classes("w-full gap-2"):

            ui.number(

                "Target Q",

                value=session.pd_q_target or q_def,

                min=0.0, step=0.05,

                on_change=lambda e: setattr(session, "pd_q_target", e.value),

            )

            ui.number(

                "Target H98",

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

            "Show solver physics live (step-by-step trace)",

            value=bool(session.pd_show_solver_live),

            on_change=lambda e: setattr(session, "pd_show_solver_live", bool(e.value)),

        )

        if str(session.pd_eval_mode) == "envelope":
            ui.label(
                "Envelope mode — optional power targets (leave P_net negative to ignore; P_net>0 varies Paux)."
            ).classes("text-caption q-mt-sm")
            with ui.grid(columns=2).classes("w-full gap-2"):
                ui.number(
                    "Target fusion power Pfus (MW)",
                    value=session.pd_pfus_target,
                    min=0.0, step=10.0,
                    on_change=lambda e: setattr(session, "pd_pfus_target", e.value),
                )
                ui.number(
                    "Target net electric P_net (MW)",
                    value=session.pd_pnet_target,
                    step=10.0,
                    on_change=lambda e: setattr(session, "pd_pnet_target", e.value),
                )

        ui.separator()

        ui.label("Optimization (experimental)").classes("text-subtitle2")

        ui.label("Random-search input proposals — SHAMS re-evaluates with frozen physics.").classes("text-caption")

        ui.checkbox(

            "Run constrained optimization before evaluate",

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

                    min=20, step=10,

                    on_change=lambda e: setattr(session, "pd_opt_iters", int(e.value or 200)),

                )

                ui.number(

                    "Seed",

                    value=session.pd_opt_seed,

                    min=0, step=1,

                    on_change=lambda e: setattr(session, "pd_opt_seed", int(e.value or 1)),

                )



    if embedded:

        _body()

        return



    with ui.expansion("Operating targets & solver", icon="gps_fixed").classes("w-full"):

        _body()

